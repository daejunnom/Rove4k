#ifndef ROVE_E_SIMD_H
#define ROVE_E_SIMD_H
#include <immintrin.h>
#include <stdint.h>

/* Fixed AVX2 submission profile; no runtime ISA selection. Sixteen signed
 * feature/weight products accumulate exactly in 32-bit lanes, without saturation.
 * The frozen model's range check proves that every partial sum fits int32_t. */
__attribute__((target("avx2"))) static inline int32_t rove_e_dot_avx2(
    const int16_t features[16], const int16_t weights[16])
{
    __m256i x = _mm256_loadu_si256((const __m256i *)features);
    __m256i w = _mm256_loadu_si256((const __m256i *)weights);
    __m256i products = _mm256_madd_epi16(x, w);
    int32_t lanes[8], score = 0;
    _mm256_storeu_si256((__m256i *)lanes, products);
    for (unsigned i = 0; i < 8; ++i) score += lanes[i];
    return score;
}
#endif
