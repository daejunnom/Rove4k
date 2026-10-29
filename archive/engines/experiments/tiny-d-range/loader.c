/* Original online range decoder; the project-owned TinyD direct-loader v3
 * bootstrap, mapping policy, entry ABI and BCJ inverse are reused verbatim.
 * Frozen provenance is documented in README.md. No external runtime code.
 */
typedef unsigned long usize;
typedef unsigned int u32;
extern const unsigned char payload[], payload_end[];
extern void enter(usize *, usize) __attribute__((noreturn));

static long sys(long number, long a, long b, long c, long d, long e, long f) {
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    long result;
    __asm__ volatile("syscall" : "=a"(result) : "a"(number), "D"(a),
                     "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return result;
}

__attribute__((noreturn)) static void bad(void) {
    sys(231, 126, 0, 0, 0, 0, 0);
    __builtin_unreachable();
}

static u32 word(const unsigned char *p) {
    return (u32)p[0] | (u32)p[1]<<8 | (u32)p[2]<<16 | (u32)p[3]<<24;
}

static void unpack(unsigned char *out) {
    const unsigned char *next = payload+20, *end = payload_end;
    if (end-payload < 25 || word(payload) != 0x31435244 ||
        payload[4] != RANGE_PROFILE || payload[5] || payload[6] || payload[7] ||
        word(payload+8) != IMAGE_SIZE || word(payload+12) != (usize)(end-next) || *next++) bad();
    unsigned count = RANGE_PROFILE ? 131328 : 65536;
    long allocation = sys(9, 0, count*2, 3, 0x22, -1, 0);
    if ((usize)allocation > (usize)-4096) bad();
    unsigned short *model = (unsigned short *)allocation;
    for (unsigned i = 0; i < count; i++) model[i] = 32768;
    u32 code = 0, width = 0xffffffff;
    for (unsigned i = 0; i < 4; i++) code = (code<<8) | *next++;
    unsigned previous = 0, older = 0, a = 1, b = 0;
    for (usize n = 0; n < IMAGE_SIZE; n++) {
        unsigned node = 1;
        for (unsigned j = 0; j < 8; j++) {
            unsigned indices[3], probability;
            indices[0] = previous*256+node;
            probability = model[indices[0]];
#if RANGE_PROFILE
            indices[1] = 65536+node;
            indices[2] = 65792+(((older*251+previous)*257+node)&65535);
            probability = (probability+model[indices[1]]+model[indices[2]])/3;
#endif
            u32 split = (width>>16)*probability;
            unsigned bit = code >= split;
            if (bit) { code -= split; width -= split; }
            else width = split;
            for (unsigned k = 0; k < (RANGE_PROFILE ? 3 : 1); k++) {
                unsigned state = model[indices[k]];
                model[indices[k]] = bit ? state-(state>>5) : state+((65536-state)>>5);
            }
            while (width < 16777216) {
                if (next == end) bad();
                width <<= 8;
                code = (code<<8) | *next++;
            }
            if (code >= width) bad();
            node = node*2+bit;
        }
        out[n] = node-256;
        older = previous; previous = out[n];
        a = (a+out[n])%65521;
        b = (b+a)%65521;
    }
    if (next != end || code || (a|(b<<16)) != word(payload+16)) bad();
    if (sys(11, allocation, count*2, 0, 0, 0, 0)) bad();
}

__attribute__((used, noreturn)) void restore(usize *stack) {
    /* An inherited READ_IMPLIES_EXEC personality can implicitly turn RW into
       executable memory. Reject it before allocating any writable image. */
    long personality = sys(135, 0xffffffffUL, 0, 0, 0, 0, 0);
    if (personality < 0 || (personality&0x400000)) bad();
    /* MAP_FIXED_NOREPLACE must reserve this exact previously-unmapped range.
       MAP_FIXED is deliberately never used: no existing mapping is replaced.
       The first and last pages remain inaccessible throughout execution. */
    long mapped = sys(9, GUARD_BASE, RESERVE_SIZE, 0, 0x100022, -1, 0);
    if ((usize)mapped != GUARD_BASE) bad();
    if (sys(10, IMAGE_BASE, IMAGE_PAGES, 3, 0, 0, 0)) bad();
    unsigned char *out = (unsigned char *)IMAGE_BASE;
    unpack(out);
    for (usize i = 0; i+4 < IMAGE_SIZE;) {
        if ((out[i]&254) == 232) {
            u32 value = (u32)out[i+1] | (u32)out[i+2] << 8 |
                        (u32)out[i+3] << 16 | (u32)out[i+4] << 24;
            value -= (u32)(i+5);
            out[i+1] = value; out[i+2] = value >> 8;
            out[i+3] = value >> 16; out[i+4] = value >> 24;
            i += 5;
        } else i++;
    }
    /* RW -> RX, never RWX. BSS consists solely of untouched anonymous zero
       pages; its page-aligned start is separate from every executable page. */
    if (sys(10, IMAGE_BASE, IMAGE_PAGES, 5, 0, 0, 0) ||
        sys(10, BSS_BASE, BSS_PAGES, 3, 0, 0, 0)) bad();
#if CHECKPOINT
    /* Audit builds stop at this exact pre-entry memory state for a parent
       /proc reader. Production candidates compile this entire branch out. */
    sys(62, sys(39, 0, 0, 0, 0, 0, 0), 19, 0, 0, 0, 0);
#endif
    enter(stack, IMAGE_ENTRY);
}

__asm__(".text\n.global _start\n.type _start,@function\n_start:\n"
        "cld\nxor %ebp,%ebp\nmov %rsp,%rdi\ncall restore\nud2\n"
        ".size _start,.-_start\n"
        ".global enter\n.type enter,@function\nenter:\n"
        "mov %rdi,%rsp\ncld\nxor %ebp,%ebp\nxor %edx,%edx\njmp *%rsi\n"
        ".size enter,.-enter\n");
