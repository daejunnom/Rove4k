/* GNU ld augment script: preserve the target's default runtime layout.
 * nv_popcount64/nv_square_bonus are individually sectioned C ABI functions.
 * Do not KEEP alternatives: the build selects exactly one object per role.
 * No arbitrary /DISCARD/ of unwind, TLS, constructor or loader sections. */
SECTIONS
{
    .nv_kernels :
    {
        *(.text.nv_popcount64)
        *(.text.nv_square_bonus)
    }
}
INSERT AFTER .text;
