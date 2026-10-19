/* Restricted static example: separate RX/RW virtual pages, no libc, dynamic
 * loader, TLS, constructors or unwind observers. This does not allow arbitrary
 * hosted binaries. Use --orphan-handling=error to reject unknown sections. */
OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)
PHDRS
{
    image PT_LOAD FILEHDR PHDRS FLAGS(5);
    data PT_LOAD FLAGS(6);
    stack PT_GNU_STACK FLAGS(6);
}
SECTIONS
{
    . = 0x400000 + SIZEOF_HEADERS;
    .text : { KEEP(*(.text.start)) *(.text .text.*) } :image
    .rodata : { *(.rodata .rodata.*) } :image
    /* Move the RW mapping into its own virtual page while retaining a compact
     * file offset with the same 4096-byte page residue. */
    . += 0x1000;
    .data : { *(.data .data.*) } :data
    .bss : { *(.bss .bss.* COMMON) } :data
    /* Keep section types separate. LLD checks even empty synthesized section
     * types; merging RELA, PROGBITS and INIT_ARRAY was only accepted by GNU ld. */
    .unsupported_code : { *(.got .got.* .igot.plt .plt .plt.* .iplt .init .fini) } :data
    .unsupported_rela : { *(.rela .rela.*) } :data
    .unsupported_init : { *(.init_array .init_array.*) } :data
    .unsupported_fini : { *(.fini_array .fini_array.*) } :data
    .unsupported_tdata : { *(.tdata .tdata.*) } :data
    .unsupported_tbss : { *(.tbss .tbss.*) } :data
    ASSERT(SIZEOF(.unsupported_code) + SIZEOF(.unsupported_rela) +
           SIZEOF(.unsupported_init) + SIZEOF(.unsupported_fini) +
           SIZEOF(.unsupported_tdata) + SIZEOF(.unsupported_tbss) == 0,
           "zero-tail example has no dynamic/TLS/constructor runtime")
    .shstrtab 0 : { *(.shstrtab) } :NONE
    /DISCARD/ :
    {
        *(.comment .note.GNU-stack .note.gnu.property .note.gnu.build-id)
        *(.eh_frame .eh_frame_hdr .gcc_except_table .gcc_except_table.*)
    }
}
