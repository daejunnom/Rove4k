// Owned static-advice example. No engine or automatic rewrite.
namespace nvcompact_example {
bool bounded_rank(int to) {
    if (to < 0 || to > 127) return false;
    return (to >> 4) == 0 || (to >> 4) == 7;
}

bool mask_guard_only(int to) {
    if (to & 0x88) return false;
    // The guard also admits 256. It does not establish to <= 127.
    return (to >> 4) == 0 || (to >> 4) == 7;
}

unsigned bounded_mask(unsigned x) {
    if (x > 7) return 0;
    return x & 7;
}

template <class T> bool template_case(T x) {
    return x == 1; // Dependent/operator-overload semantics are withheld.
}
}
