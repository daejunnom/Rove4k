ENTRY(_start)
PHDRS {
    image PT_LOAD FILEHDR PHDRS FLAGS(5);
    memory PT_LOAD FLAGS(6);
    stack PT_GNU_STACK FLAGS(6);
}
SECTIONS {
    . = 0x400000 + SIZEOF_HEADERS;
    .text : { *(.text .text.*) } :image
    .rodata : { *(.rodata .rodata.*) } :image
    . = ALIGN(4096);
    .data : { *(.data .data.*) } :memory
    .bss (NOLOAD) : { *(.bss .bss.*) *(COMMON) } :memory
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.gnu*) }
}
