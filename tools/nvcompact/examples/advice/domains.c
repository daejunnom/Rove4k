/* Owned examples for read-only domain/n-version advice. No generated rewrite. */
#include <stdio.h>

int bounded_rank(int to) {
    if (to < 0 || to > 127) return -1;
    return (to>>4)==0||(to>>4)==7;
}

int board_rank(int to) {
    if (to < 0 || to > 127 || (to & 0x88)) return -1;
    return (to>>4)==0||(to>>4)==7;
}

int mask_guard_only(int to) {
    if (to & 0x88) return -1;
    /* 256 passes this guard. It does not establish the rank input bound. */
    return (to>>4)==0||(to>>4)==7;
}

int observed_rank(int to) {
    /* Caller samples are separate from this function's static domain. */
    return (to>>4)==0||(to>>4)==7;
}

int sparse_result(int condition) {
    int value = condition ? 1 : 9;
    return value == 1 || value == 9;
}

int main(int argc, char **argv) {
    int sum = 0;
    (void)argv;
    for (int to = 0; to < 128; ++to) {
        if (bounded_rank(to) != observed_rank(to)) return 1;
        sum += observed_rank(to);
    }
    /* An optional second profile contains values outside the first closure. */
    if (argc > 1) sum += observed_rank(135) + observed_rank(256);
    printf("%d\n", sum);
    return !sparse_result(argc);
}
