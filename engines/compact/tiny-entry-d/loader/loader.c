/* Project-owned context unpack plus the existing TinyD guarded restore.
 * No upstream decoder source, interpreter, libc, TLS or external program.
 * The software context decoder is independently written from its format.
 */
typedef unsigned long usize;
typedef unsigned int u32;
extern const unsigned char payload[], payload_end[];
extern void enter(usize *, usize) __attribute__((noreturn));
#include "decoder.h"
#define CONTEXT_BYTES 33554432UL

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

__attribute__((used, noreturn)) void restore(usize *stack) {
    /* Preserve the qualified restore's personality and mapping boundary. */
    long personality = sys(135, 0xffffffffUL, 0, 0, 0, 0, 0);
    if (personality < 0 || (personality&0x400000)) bad();
    long mapped = sys(9, GUARD_BASE, RESERVE_SIZE, 0, 0x100022, -1, 0);
    if ((usize)mapped != GUARD_BASE) bad();
    if (sys(10, IMAGE_BASE, IMAGE_PAGES, 3, 0, 0, 0)) bad();
    unsigned char *out = (unsigned char *)IMAGE_BASE;
    /* The fixed H24 table is private, writable and initially kernel-zero.
       It is separate from both RX images and released before native entry. */
    long context = sys(9, 0, CONTEXT_BYTES, 3, 0x22, -1, 0);
    if (!context || (usize)context >= (usize)-4095) bad();
    if (context_decode(out, IMAGE_SIZE, payload, payload_end,
                       (unsigned char *)context)) bad();
    if (sys(11, context, CONTEXT_BYTES, 0, 0, 0, 0)) bad();
    for (usize i = 0; i+4 < IMAGE_SIZE;) {
        if ((out[i]&254) == 232) {
            u32 value;
            __builtin_memcpy(&value, out+i+1, sizeof value);
            value -= (u32)(i+5);
            __builtin_memcpy(out+i+1, &value, sizeof value);
            i += 5;
        } else i++;
    }
    /* RW -> RX, never RWX; only separate anonymous BSS becomes RW. */
    if (sys(10, IMAGE_BASE, IMAGE_PAGES, 5, 0, 0, 0) ||
        sys(10, BSS_BASE, BSS_PAGES, 3, 0, 0, 0)) bad();
#if CHECKPOINT
    /* Audit only: context is unmapped, RX/BSS protections are final, and
       native entry has not initialized BSS or created workers. */
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
