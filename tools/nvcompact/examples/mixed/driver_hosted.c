#include <stdio.h>
#include "kernels.h"

int main(void)
{
    unsigned char input[16], output[8];
    for (;;) {
        size_t got = fread(input, 1, sizeof input, stdin);
        if (got == 0)
            return ferror(stdin) ? 3 : (fflush(stdout) == 0 ? 0 : 3);
        if (got != sizeof input)
            return ferror(stdin) ? 3 : 2;
        if (nv_process(input, output) != 0)
            return 2;
        if (fwrite(output, 1, sizeof output, stdout) != sizeof output)
            return 3;
    }
}
