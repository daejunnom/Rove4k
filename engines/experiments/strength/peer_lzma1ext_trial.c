/* Build-only experiment: LZMA1EXT without an end marker, in a .lzma stream.
 * This helper is never part of the engine submission or its runtime. */
#include <lzma.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INPUT_LIMIT (1U << 20)

static int parse_u32(const char *s, uint32_t *value) {
    char *end;
    unsigned long v;
    if (!*s || *s == '-' || *s == '+') return 0;
    errno = 0;
    v = strtoul(s, &end, 10);
    if (errno || *end || v > UINT32_MAX) return 0;
    *value = (uint32_t)v;
    return 1;
}

static void put_le(unsigned char *p, uint64_t value, unsigned n) {
    while (n--) { *p++ = (unsigned char)value; value >>= 8; }
}

static int power_of_two(uint32_t value) {
    return value && !(value & (value - 1));
}

static int standard_dict(uint32_t value) {
    return power_of_two(value) || (value % 3 == 0 && power_of_two(value / 3));
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--version") == 0) {
#ifdef LZMA_FILTER_LZMA1EXT
        printf("header=%s runtime=%s header_number=%u runtime_number=%u ext=%d\n",
               LZMA_VERSION_STRING, lzma_version_string(), (unsigned)LZMA_VERSION,
               (unsigned)lzma_version_number(),
               lzma_filter_encoder_is_supported(LZMA_FILTER_LZMA1EXT) ? 1 : 0);
#else
        printf("header=%s runtime=%s header_number=%u runtime_number=%u ext=0\n",
               LZMA_VERSION_STRING, lzma_version_string(), (unsigned)LZMA_VERSION,
               (unsigned)lzma_version_number());
#endif
        return ferror(stdout) ? 1 : 0;
    }
#ifndef LZMA_FILTER_LZMA1EXT
    (void)argc; (void)argv;
    fputs("LZMA1EXT unavailable in liblzma headers\n", stderr);
    return 3;
#else
    uint32_t lc, lp, pb, mf, nice, dict, depth;
    lzma_options_lzma opts;
    lzma_filter filters[2];
    unsigned char *input, *output;
    size_t length, output_pos = 13, output_cap;
    lzma_ret ret;
    if (argc != 8 || !parse_u32(argv[1], &lc) || !parse_u32(argv[2], &lp)
        || !parse_u32(argv[3], &pb) || !parse_u32(argv[4], &mf)
        || !parse_u32(argv[5], &nice) || !parse_u32(argv[6], &dict)
        || !parse_u32(argv[7], &depth) || lc > 4 || lp > 4 || lc + lp > 4
        || pb > 4 || (mf != LZMA_MF_HC3 && mf != LZMA_MF_HC4
        && mf != LZMA_MF_BT2 && mf != LZMA_MF_BT3 && mf != LZMA_MF_BT4)
        || nice < 8 || nice > 273 || dict < 4096 || dict > (64U << 20)
        || !standard_dict(dict)
        || depth > 100000) {
        fputs("invalid LZMA1EXT trial parameters\n", stderr); return 2;
    }
    if (!lzma_filter_encoder_is_supported(LZMA_FILTER_LZMA1EXT)) {
        fputs("LZMA1EXT unavailable in liblzma runtime\n", stderr); return 3;
    }
    if (lzma_lzma_preset(&opts, 9 | LZMA_PRESET_EXTREME)) {
        fputs("liblzma preset unavailable\n", stderr); return 3;
    }
    opts.lc = lc; opts.lp = lp; opts.pb = pb; opts.mf = (lzma_match_finder)mf;
    opts.nice_len = nice; opts.dict_size = dict; opts.depth = depth;
    opts.ext_flags = 0; /* A real no-EOS encoding, not truncation. */
    filters[0].id = LZMA_FILTER_LZMA1EXT; filters[0].options = &opts;
    filters[1].id = LZMA_VLI_UNKNOWN; filters[1].options = NULL;
    if (lzma_raw_encoder_memusage(filters) > (UINT64_C(1) << 30)) {
        fputs("LZMA1EXT encoder memory exceeds trial limit or options invalid\n", stderr); return 2;
    }
    input = malloc(INPUT_LIMIT + 1U);
    if (!input) { fputs("input allocation failed\n", stderr); return 1; }
    length = fread(input, 1, INPUT_LIMIT + 1U, stdin);
    if (ferror(stdin) || length > INPUT_LIMIT) {
        free(input); fputs("input read failed or exceeds limit\n", stderr); return 1;
    }
    output_cap = 2U * length + 4096U;
    output = malloc(output_cap);
    if (!output) { free(input); fputs("output allocation failed\n", stderr); return 1; }
    output[0] = (unsigned char)((pb * 5U + lp) * 9U + lc);
    put_le(output + 1, dict, 4); put_le(output + 5, length, 8);
    ret = lzma_raw_buffer_encode(filters, NULL, input, length,
                                 output, &output_pos, output_cap);
    free(input);
    if (ret != LZMA_OK) {
        fprintf(stderr, "LZMA1EXT encoding failed: %d\n", (int)ret); free(output); return 1;
    }
    if (fwrite(output, 1, output_pos, stdout) != output_pos || fflush(stdout)) {
        free(output); fputs("output write failed\n", stderr); return 1;
    }
    free(output);
    return 0;
#endif
}
