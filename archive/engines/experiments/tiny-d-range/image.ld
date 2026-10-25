ENTRY(_start)
PHDRS { image PT_LOAD FILEHDR PHDRS FLAGS(5); stack PT_GNU_STACK FLAGS(6); }
SECTIONS {
    . = 0x10000000 + SIZEOF_HEADERS;
    .text : { *(.text .text.*) } :image
    .rodata : { *(.rodata .rodata.*) *(.payload) } :image
    .unexpected : { *(.data .data.*) *(.bss .bss.*) *(COMMON) } :image
    ASSERT(SIZEOF(.unexpected) == 0, "loader must have no writable globals")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.gnu*) }
}
