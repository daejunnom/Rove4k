#include <stdint.h>

extern uint32_t nv_probe(uint32_t index, uint32_t value);

static long syscall3(long number, long fd, void *buffer, unsigned long size)
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
    for (;;) {
        uint32_t input[2], output;
        unsigned long done = 0;
        while (done < sizeof input) {
            long got = syscall3(0, 0, (char *)input + done, sizeof input - done);
            if (got == -4) continue;
            if (got < 0) return 3;
            if (!got) return done ? 2 : 0;
            done += (unsigned long)got;
        }
        if (input[0] >= 8192) return 2;
        output = nv_probe(input[0], input[1]);
        done = 0;
        while (done < sizeof output) {
            long sent = syscall3(1, 1, (char *)&output + done, sizeof output - done);
            if (sent == -4) continue;
            if (sent <= 0) return 3;
            done += (unsigned long)sent;
        }
    }
}
