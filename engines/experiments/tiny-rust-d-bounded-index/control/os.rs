//! Linux x86-64 only. No libc, TLS, pthread or allocator runtime.
use core::{arch::{asm, global_asm}, sync::atomic::{AtomicI32, AtomicU32, Ordering}};

global_asm!(r#"
.section .text._start,"ax"
.global _start
.type _start,@function
_start:
    cld
    xor ebp,ebp
    and rsp,-16
    call engine_main
    mov eax,231
    xor edi,edi
    syscall
    ud2
.size _start,.-_start
.section .text.spawn,"ax"
.global raw_spawn
.type raw_spawn,@function
raw_spawn:
    and rdi,-16
    sub rdi,16
    mov [rdi],rdx
    mov r10,rsi
    mov rsi,rdi
    mov rdx,r10
    mov edi,0x350f00
    xor r8d,r8d
    mov eax,56
    syscall
    test rax,rax
    jnz 1f
    xor ebp,ebp
    mov rdi,[rsp]
    call worker_entry
    mov eax,60
    xor edi,edi
    syscall
    ud2
1:  ret
.size raw_spawn,.-raw_spawn
.section .text.memory,"ax"
.global memcpy
.type memcpy,@function
memcpy:
    mov rax,rdi
    mov rcx,rdx
    rep movsb
    ret
.size memcpy,.-memcpy
.global memmove
.type memmove,@function
memmove:
    mov rax,rdi
    mov rcx,rdx
    cmp rdi,rsi
    jbe 2f
    lea r8,[rsi+rdx]
    cmp rdi,r8
    jae 2f
    test rdx,rdx
    jz 3f
    lea rdi,[rdi+rdx-1]
    lea rsi,[rsi+rdx-1]
    std
    rep movsb
    cld
    ret
2:  rep movsb
3:  ret
.size memmove,.-memmove
.global memset
.type memset,@function
memset:
    mov r8,rdi
    mov eax,esi
    mov rcx,rdx
    rep stosb
    mov rax,r8
    ret
.size memset,.-memset
.global memcmp
.global bcmp
.type memcmp,@function
.type bcmp,@function
memcmp:
bcmp:
    xor eax,eax
    test rdx,rdx
    jz 5f
4:  movzx eax,byte ptr [rdi]
    movzx r8d,byte ptr [rsi]
    sub eax,r8d
    jne 5f
    inc rdi
    inc rsi
    dec rdx
    jnz 4b
5:  ret
.size memcmp,.-memcmp
.size bcmp,.-bcmp
.section .note.GNU-stack,"",@progbits
"#);

unsafe extern "C" {fn raw_spawn(top:*mut u8, tid:*mut i32, argument:*mut u8)->isize;}

#[inline(always)]
unsafe fn syscall(n:usize,a:usize,b:usize,c:usize,d:usize,e:usize,f:usize)->isize {
    let result:isize;
    unsafe {asm!("syscall",inlateout("rax")n=>result,in("rdi")a,in("rsi")b,in("rdx")c,
        in("r10")d,in("r8")e,in("r9")f,lateout("rcx")_,lateout("r11")_,options(nostack));}
    result
}
pub fn fatal(status:usize)->! {unsafe{syscall(231,status,0,0,0,0,0);}loop{core::hint::spin_loop();}}
pub fn allocate(bytes:usize)->*mut u8 {
    let value=unsafe{syscall(9,0,bytes,3,0x22,usize::MAX,0)};
    if value<0 {fatal(111);}value as *mut u8
}
pub unsafe fn release(address:*mut u8,bytes:usize) {
    if unsafe{syscall(11,address as usize,bytes,0,0,0,0)}!=0 {fatal(112);}
}
pub const STACK:usize=1024*1024;
pub const STACK_MAP:usize=STACK+8192;
pub fn stack()->*mut u8 {
    let p=unsafe{syscall(9,0,STACK_MAP,0,0x22,usize::MAX,0)};
    if p<0 {fatal(113);}let base=p as *mut u8;
    if unsafe{syscall(10,base.add(4096)as usize,STACK,3,0,0,0)}!=0 {fatal(114);}base
}
pub unsafe fn spawn(base:*mut u8,tid:&AtomicI32,argument:*mut u8) {
    // PARENT_SETTID and CHILD_CLEARTID share this aligned atomic word. The
    // positive clone return must not overwrite a child that already cleared it.
    let result=unsafe{raw_spawn(base.add(4096+STACK),tid.as_ptr(),argument)};
    if result<0 {fatal(115);}
}
pub fn wait(word:&AtomicU32,value:u32) {
    let result=unsafe{syscall(202,word.as_ptr()as usize,128,value as usize,0,0,0)};
    if result<0 && result != -4 && result != -11 {fatal(116);}
}
pub fn wake(word:&AtomicU32) {
    if unsafe{syscall(202,word.as_ptr()as usize,129,i32::MAX as usize,0,0,0)}<0 {fatal(117);}
}
pub fn join(tid:&AtomicI32) {
    loop {
        let value=tid.load(Ordering::Acquire);if value==0 {return;}
        // Kernel clear_child_tid uses shared FUTEX_WAKE, never PRIVATE.
        let result=unsafe{syscall(202,tid.as_ptr()as usize,0,value as usize,0,0,0)};
        if result<0 && result != -4 && result != -11 {fatal(118);}
    }
}
pub fn millis()->u64 {
    let mut time=[0u64;2];
    if unsafe{syscall(228,1,time.as_mut_ptr()as usize,0,0,0,0)}!=0 {fatal(119);}
    time[0].saturating_mul(1000).saturating_add(time[1]/1_000_000)
}
pub fn read(bytes:&mut[u8])->isize {
    loop {let n=unsafe{syscall(0,0,bytes.as_mut_ptr()as usize,bytes.len(),0,0,0)};if n != -4{return n;}}
}
static OUTPUT:AtomicU32=AtomicU32::new(0);
pub fn output(mut bytes:&[u8]) {
    while OUTPUT.compare_exchange(0,1,Ordering::Acquire,Ordering::Relaxed).is_err(){wait(&OUTPUT,1);}
    while !bytes.is_empty() {
        let n=unsafe{syscall(1,1,bytes.as_ptr()as usize,bytes.len(),0,0,0)};
        if n == -4 {continue;}if n<=0 {fatal(120);}bytes=&bytes[n as usize..];
    }
    OUTPUT.store(0,Ordering::Release);wake(&OUTPUT);
}
