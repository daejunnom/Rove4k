ENTRY(_start)
PHDRS {
  text PT_LOAD FILEHDR PHDRS FLAGS(5);
  data PT_LOAD FLAGS(6);
  stack PT_GNU_STACK FLAGS(6);
}
SECTIONS {
  . = 0x400000 + SIZEOF_HEADERS;
  .text : { *(.text._start) *(.text*) } :text
  .rodata : { *(.rodata*) *(.data.rel.ro*) } :text
  . = ALIGN(4096);
  .data : { *(.data*) *(.got*) } :data
  .bss (NOLOAD) : { *(.bss*) *(COMMON) } :data
  /DISCARD/ : { *(.eh_frame*) *(.gcc_except_table*) *(.comment*) *(.note*) }
}
