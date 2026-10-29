/* Dedicated Linux x86-64 restore for the two build-time-admitted TinyD images.
 * No interpreter, libc, TLS, file creation, ELF parser or external program.
 * Runtime code is original to this experiment, except the internal LZ run
 * format/inverse follows our repository's existing generic own-ELF loader.
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

#if CODEC_FIXED
typedef struct {
    const unsigned char *next, *end;
    u32 bits, count;
} Bits;

static unsigned bits(Bits *r, unsigned count) {
    while (r->count < count) {
        if (r->next == r->end) bad();
        r->bits |= (u32)*r->next++ << r->count;
        r->count += 8;
    }
    unsigned result = r->bits & ((1u << count)-1);
    r->bits >>= count;
    r->count -= count;
    return result;
}

static unsigned symbol(Bits *r) {
    unsigned code = 0;
    for (unsigned i = 0; i < 7; i++) code = 2*code + bits(r, 1);
    if (code < 24) return code + 256;
    code = 2*code + bits(r, 1);
    if (code < 192) return code - 48;
    if (code < 200) return code + 88;
    code = 2*code + bits(r, 1);
    return code - 256;
}

static void unpack(unsigned char *out) {
    Bits r = {payload, payload_end, 0, 0};
    /* One final fixed-Huffman RFC1951 block; the producer rejects any other
       shape rather than embedding unused stored/dynamic-block machinery. */
    if (bits(&r, 3) != 3) bad();
    usize n = 0;
    for (;;) {
        unsigned code = symbol(&r);
        if (code < 256) {
            if (n == IMAGE_SIZE) bad();
            out[n++] = code;
            continue;
        }
        if (code == 256) break;
        if (code > 285) bad();
        unsigned count;
        if (code < 265) count = code - 254;
        else if (code == 285) count = 258;
        else {
            unsigned extra = (code-261)/4;
            count = ((4 + ((code-265)&3)) << extra) + 3 + bits(&r, extra);
        }
        unsigned distance = 0;
        for (unsigned i = 0; i < 5; i++) distance = 2*distance + bits(&r, 1);
        if (distance > 29) bad();
        if (distance < 4) distance++;
        else {
            unsigned extra = distance/2 - 1;
            distance = ((2 + (distance&1)) << extra) + 1 + bits(&r, extra);
        }
        if (distance > n || count > IMAGE_SIZE-n) bad();
        do { out[n] = out[n-distance]; n++; } while (--count);
    }
    if (n != IMAGE_SIZE || r.next != r.end || r.bits) bad();
}
#else
static void unpack(unsigned char *out) {
    const unsigned char *p = payload;
    usize n = 0;
    while (p != payload_end) {
        unsigned count = *p++;
        if (count < 128) {
            count++;
            if ((usize)(payload_end-p) < count || count > IMAGE_SIZE-n) bad();
            do { out[n++] = *p++; } while (--count);
        } else {
            count = (count&127)+3;
            if (payload_end-p < 2 || count > IMAGE_SIZE-n) bad();
            unsigned distance = (unsigned)p[0] | (unsigned)p[1] << 8;
            p += 2;
            if (!distance || distance > n) bad();
            do { out[n] = out[n-distance]; n++; } while (--count);
        }
    }
    if (n != IMAGE_SIZE) bad();
}
#endif

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
