/* Restricted executable profile for the no-libc example, GNU ld ELF x86-64.
 * Not a drop-in script for hosted C/Rust programs. No dynamic loader, writable
 * globals, constructors, TLS, unwinding or language runtime are supported.
 * Two program headers: RX code/data (including ELF headers), and a RW stack.
 * The linker must fail for unexpected allocatable sections; invoke with
 * --orphan-handling=error. This restriction is a profile, not a fallback.
 */
OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

PHDRS
{
    image PT_LOAD FILEHDR PHDRS FLAGS(5);
    stack PT_GNU_STACK FLAGS(6);
}

SECTIONS
{
    . = 0x400000 + SIZEOF_HEADERS;
    .text :
    {
        KEEP(*(.text.start))
        *(.text .text.*)
    } :image
    .rodata : { *(.rodata .rodata.*) } :image
    .data : { *(.data .data.*) } :image
    .bss : { *(.bss .bss.* COMMON) } :image
    ASSERT(SIZEOF(.data) == 0, "compact profile requires no writable data")
    ASSERT(SIZEOF(.bss) == 0, "compact profile requires no writable bss")
    /* GNU ld synthesizes these sections even when they are empty. Name them
     * explicitly and reject actual runtime relocation/indirection contents. */
    .unsupported_runtime :
    {
        *(.got .got.* .igot.plt .plt .plt.* .iplt .rela .rela.*)
    } :image
    ASSERT(SIZEOF(.unsupported_runtime) == 0,
           "compact profile requires no GOT/PLT or runtime relocations")
    /DISCARD/ :
    {
        *(.comment .note.GNU-stack .note.gnu.property .note.gnu.build-id)
        *(.eh_frame .eh_frame_hdr .gcc_except_table .gcc_except_table.*)
    }
}
