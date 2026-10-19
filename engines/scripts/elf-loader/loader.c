/* Linux x86-64 only. No libc, interpreter, temporary pathname or external tool. */
typedef unsigned long usize;
_Static_assert(sizeof(unsigned) == 4, "branch filter requires 32-bit unsigned");
extern const unsigned char packed_payload[], packed_payload_end[];

static long call6(long number, long a, long b, long c, long d, long e, long f) {
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    long result;
    __asm__ volatile ("syscall" : "=a"(result) : "a"(number), "D"(a),
                      "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                      : "rcx", "r11", "memory");
    return result;
}

__attribute__((noreturn)) static void failed(void) {
    static const char message[] = "Rove4k ELF restore failed\n";
    call6(1, 2, (long)message, sizeof(message)-1, 0, 0, 0);
    call6(60, 126, 0, 0, 0, 0, 0);
    __builtin_unreachable();
}

__attribute__((noreturn, used)) void restore(usize *stack) {
    char **argv = (char **)(stack+1);
    char **env = argv+stack[0]+1;
    long address = call6(9, 0, OUTPUT_SIZE, 3, 0x22, -1, 0);
    if ((usize)address >= (usize)-4095) failed();
    unsigned char *out = (unsigned char *)address;
    usize source = (usize)packed_payload, end = (usize)packed_payload_end, n = 0;
    while (source < end) {
        unsigned count = *(const unsigned char *)source++;
        if (count < 128) {
            count++;
            if (source+count > end || n+count > OUTPUT_SIZE) failed();
            do { out[n++] = *(const unsigned char *)source++; } while (--count);
        } else {
            count = (count & 127)+3;
            if (source+2 > end || n+count > OUTPUT_SIZE) failed();
            unsigned distance = *(const unsigned char *)source++;
            distance |= (unsigned)*(const unsigned char *)source++ << 8;
            if (!distance || distance > n) failed();
            do { out[n] = out[n-distance]; n++; } while (--count);
        }
    }
    if (n != OUTPUT_SIZE) failed();
#if BRANCH_FILTER
    /* Inverse of the whole-file E8/E9 transform. The scan skips all four
       operand bytes, including any E8/E9 bytes inside an operand. Unsigned
       arithmetic deliberately wraps modulo 2^32; bytewise loads avoid alignment
       and pointer-aliasing assumptions. */
    for (usize i = 0; i+4 < OUTPUT_SIZE;) {
        if ((out[i] & 254) == 232) {
            unsigned value = (unsigned)out[i+1] | (unsigned)out[i+2] << 8 |
                             (unsigned)out[i+3] << 16 | (unsigned)out[i+4] << 24;
            value -= (unsigned)(i+5);
            out[i+1] = value;
            out[i+2] = value >> 8;
            out[i+3] = value >> 16;
            out[i+4] = value >> 24;
            i += 5;
        } else i++;
    }
#endif
    /* MFD_EXEC is required by newer memfd policies, absent on older kernels. */
    long fd = call6(319, (long)"rove4k", 17, 0, 0, 0, 0);
    if (fd == -22) fd = call6(319, (long)"rove4k", 1, 0, 0, 0, 0);
    if (fd < 0) failed();
    n = 0;
    while (n < OUTPUT_SIZE) {
        long written = call6(1, fd, (long)(out+n), OUTPUT_SIZE-n, 0, 0, 0);
        if (written == -4) continue;
        if (written <= 0) failed();
        n += (usize)written;
    }
    /* AT_EMPTY_PATH; the kernel supplies the restored ELF's normal auxv. */
    call6(322, fd, (long)"", (long)argv, (long)env, 0x1000, 0);
    failed();
}

__asm__(".text\n.global _start\n.type _start,@function\n_start:\n"
        "xor %ebp,%ebp\nmov %rsp,%rdi\ncall restore\nud2\n"
        ".size _start,.-_start\n");
