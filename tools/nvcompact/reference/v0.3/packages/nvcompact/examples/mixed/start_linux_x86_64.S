/* Process entry has no return address. Align before the C ABI call. */
.section .text.start,"ax",@progbits
.global _start
.type _start,@function
_start:
    xor %ebp,%ebp
    and $-16,%rsp
    call nv_main
    mov %eax,%edi
    mov $60,%eax
    syscall
    ud2
.size _start,.-_start
.section .note.GNU-stack,"",@progbits
