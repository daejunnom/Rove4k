ENTRY(_start)
PHDRS { image PT_LOAD FILEHDR PHDRS FLAGS(5); stack PT_GNU_STACK FLAGS(6); }
SECTIONS {
    . = 0x400000 + SIZEOF_HEADERS;
    .text : { *(.text .text.*) } :image
    .rodata : { *(.rodata .rodata.*) *(.payload) } :image
    .unexpected_data : { *(.data .data.*) *(.bss .bss.*) *(COMMON) } :image
    ASSERT(SIZEOF(.unexpected_data) == 0, "loader must have no writable globals")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.gnu*) }
}
