.text
.global _start
.type _start,@function
_start:
    xor %ebp,%ebp
    and $-16,%rsp
    call main
    mov %eax,%edi
    mov $231,%eax
    syscall
    ud2
.size _start,.-_start

/* long spawn(void (*fn)(void *), void *arg, void *stack_top, int *tid);
 * CLONE_PARENT_SETTID publishes tid before the parent returns. The kernel
 * clears it and performs a shared futex wake on thread exit. No TLS is used. */
.global spawn
.type spawn,@function
spawn:
    and $-16,%rdx
    sub $16,%rdx
    mov %rdi,(%rdx)
    mov %rsi,8(%rdx)
    mov %rdx,%rsi
    mov %rcx,%rdx
    mov %rcx,%r10
    xor %r8d,%r8d
    mov $0x350f00,%edi
    mov $56,%eax
    syscall
    test %rax,%rax
    jnz 1f
    pop %rax
    pop %rdi
    call *%rax
    xor %edi,%edi
    mov $60,%eax
    syscall
    ud2
1:  ret
.size spawn,.-spawn
.section .note.GNU-stack,"",@progbits
