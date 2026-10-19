#include "kernels.h"

#if !defined(__linux__) || !defined(__x86_64__)
#error "This freestanding example targets Linux x86-64 only."
#endif

/* Linux x86-64 syscall ABI. No libc, constructors, TLS, heap or signals
 * are used by this profile. rcx/r11 and memory are clobbered by syscall. */
static long nv_syscall3(long number, long fd, void *buffer, unsigned long size)
{
    long result;
    __asm__ volatile("syscall"
        : "=a"(result)
        : "a"(number), "D"(fd), "S"(buffer), "d"(size)
        : "rcx", "r11", "memory", "cc");
    return result;
}

int nv_main(void)
{
    unsigned char input[16], output[8];
    for (;;) {
        unsigned long done = 0;
        while (done < sizeof input) {
            long got = nv_syscall3(0, 0, input + done, sizeof input - done);
            if (got == -4) /* EINTR */
                continue;
            if (got < 0)
                return 3;
            if (got == 0)
                return done == 0 ? 0 : 2;
            done += (unsigned long)got;
        }
        if (nv_process(input, output) != 0)
            return 2;
        done = 0;
        while (done < sizeof output) {
            long wrote = nv_syscall3(1, 1, output + done, sizeof output - done);
            if (wrote == -4)
                continue;
            if (wrote <= 0)
                return 3;
            done += (unsigned long)wrote;
        }
    }
}
