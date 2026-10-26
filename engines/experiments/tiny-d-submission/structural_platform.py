"""Source-owned D allocation, clone-entry and ELF-layout experiments.

Apply after the first structural full candidate. These are optional cost
experiments, not changes to the maintained kernel mapping admission. Every
alternative keeps non-executable stacks and separate RX/RW mappings. Allocation
ownership and delayed first touch are explicit, so startup costs are not
silently presented as search-speed improvements.
"""

OPTIONS = {
    'stack-arena': 'one stack arena, retaining per-worker guard pages and TT first touch',
    'single-arena': 'one anonymous allocation for TT and all guarded stacks',
    'static-stacks': 'zero-fill ELF storage for the same guarded worker stacks',
    'fixed-worker-entry': 'specialize clone entry for the only nonreturning callback',
    'lazy-tt-zero': 'defer anonymous TT page first touch from startup to search',
    'inline-allocate': 'allow the compiler to inline the allocation wrapper',
    'noinline-position': 'share the position transaction as one callable body',
    'noinline-resolver': 'retain one move resolver across its two consumers',
    'noinline-clock': 'retain one syscall clock conversion body',
    'abort-startup': 'share the existing exit-group failure owner during startup',
    'last-startup-wake': 'only the last first-touch arrival wakes the input thread',
    'shared-arrival': 'one completion owner for startup and search, with explicit output phase',
    'nul-tokens': 'terminate tokens in the owned input buffer instead of returning pointer-length pairs',
    'rodata-first': 'place immutable constants before executable code in the RX load',
    'text-name-order': 'sort retained function sections by name at link time',
    'rodata-name-order': 'sort retained immutable sections by name at link time',
}


def replace(text, before, after):
    if text.count(before) != 1:
        raise ValueError('platform source applicability differs: ' + before[:72])
    return text.replace(before, after, 1)


def apply(files, options=()):
    """Return a new readable six-file mapping; no I/O or compilation."""
    if len(options) != len(set(options)) or set(options) - OPTIONS.keys():
        raise ValueError('unknown or duplicate platform option')
    if len(set(options) & {'stack-arena', 'single-arena', 'static-stacks'}) > 1:
        raise ValueError('choose one stack-storage owner')
    if 'last-startup-wake' in options and 'shared-arrival' in options:
        raise ValueError('choose one startup arrival representation')
    result = dict(files)
    runtime = files['runtime.c'].decode()
    start = files['start.S'].decode()
    linker = files['image.ld'].decode()
    init = 'table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;'
    stack = 'char *stack=allocate(1048576+4096);if(!stack){status=2;break;}'
    if 'stack-arena' in options:
        runtime = replace(runtime, init,
            init + '\n    char *arena=allocate((size_t)WORKERS*(1048576+4096));if(!arena)return 2;')
        runtime = replace(runtime, stack,
            'char *stack=arena+(size_t)created*(1048576+4096);')
    if 'single-arena' in options:
        runtime = replace(runtime, init,
            'size_t table_bytes=((size_t)1<<TT_BITS)*sizeof *table;\n'
            '    table=allocate(table_bytes+(size_t)WORKERS*(1048576+4096));if(!table)return 2;')
        runtime = replace(runtime, stack,
            'char *stack=(char *)table+table_bytes+(size_t)created*(1048576+4096);')
    if 'static-stacks' in options:
        runtime = replace(runtime, 'Worker workers[WORKERS];',
            'Worker workers[WORKERS];\n'
            'static _Alignas(4096) char worker_stacks[WORKERS][1048576+4096];')
        runtime = replace(runtime, stack, 'char *stack=worker_stacks[created];')
    if 'fixed-worker-entry' in options:
        runtime = replace(runtime, 'extern long spawn(void (*)(void *),void *,void *);',
            'extern long spawn(void *,void *);')
        runtime = replace(runtime, 'static void work(void *p){',
            '__attribute__((used,externally_visible)) _Noreturn void work(void *p){')
        runtime = replace(runtime, 'spawn(work,workers+created,stack+1048576+4096)',
            'spawn(workers+created,stack+1048576+4096)')
        begin = start.index('/* long spawn(')
        end = start.index('.size spawn,.-spawn', begin) + len('.size spawn,.-spawn')
        start = start[:begin] + '''/* Only work is admitted here. It never returns. The saved argument occupies
 * the unused return-address slot, leaving SysV entry rsp congruent to 8 mod 16.
 * Parent and child both retain the original clone flags and return contract. */
.global spawn
.type spawn,@function
spawn:
    and $-16,%rsi
    sub $8,%rsi
    mov %rdi,(%rsi)
    mov $0x50f00,%edi
    mov $56,%eax
    syscall
    test %rax,%rax
    jnz 1f
    mov (%rsp),%rdi
    jmp work
1:  ret
.size spawn,.-spawn''' + start[end:]
    if 'lazy-tt-zero' in options:
        first = runtime.index('    /* Entry=16B, pages=256 entries:')
        end = runtime.index('    atomic_fetch_sub_explicit(&pending,1,memory_order_release);', first)
        runtime = runtime[:first] + '''    /* Fresh anonymous storage is zero-filled. This alternative intentionally
     * moves physical page first touch to TT access; NUMA placement and initial
     * search latency differ from the explicit parallel prefault baseline. */
''' + runtime[end:]
    for option, before, after in (
            ('inline-allocate', 'static __attribute__((noinline)) void *allocate(', 'static void *allocate('),
            ('noinline-position', 'static void set_position(', 'static __attribute__((noinline)) void set_position('),
            ('noinline-resolver', 'static Move resolve_move(', 'static __attribute__((noinline)) Move resolve_move('),
            ('noinline-clock', 'uint64_t now(void){', '__attribute__((noinline)) uint64_t now(void){')):
        if option in options:
            runtime = replace(runtime, before, after)
    if 'last-startup-wake' in options:
        runtime = replace(runtime,
            'atomic_fetch_sub_explicit(&pending,1,memory_order_release);wake(&pending);',
            'if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==1)wake(&pending);')
    if 'shared-arrival' in options:
        runtime = replace(runtime, 'Worker *w=p;int seen=0;', 'Worker *w=p;int seen=0,report=0;')
        runtime = replace(runtime,
            '''atomic_fetch_sub_explicit(&pending,1,memory_order_release);wake(&pending);
    for(;;){
        int current=atomic_load_explicit(&epoch,memory_order_acquire);
        if(current==seen){futex_wait(&epoch,seen,1);continue;}
        seen=current;w->best=0;think(w,&position);
        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){
            result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);
        }
    }
}''',
            '''for(;;){
        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){
            if(report)result();
            atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);
        }
        report=1;
        int current;
        while((current=atomic_load_explicit(&epoch,memory_order_acquire))==seen)
            futex_wait(&epoch,seen,1);
        seen=current;w->best=0;think(w,&position);
    }
}''')
        runtime = replace(runtime,
            'atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);',
            'atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);')
    if 'abort-startup' in options:
        runtime = replace(runtime, 'int created=0,status=0;char line[32768];',
            'int created=0;char line[32768];')
        runtime = replace(runtime, 'if(!table)return 2;', 'if(!table)abort();')
        if 'stack-arena' in options:
            runtime = replace(runtime, 'if(!arena)return 2;', 'if(!arena)abort();')
        if not set(options) & {'stack-arena', 'single-arena', 'static-stacks'}:
            runtime = replace(runtime, 'if(!stack){status=2;break;}', 'if(!stack)abort();')
        runtime = replace(runtime, '<0){status=2;break;}', '<0)abort();')
        runtime = replace(runtime, '    if(status)goto shutdown;\n', '')
        runtime = replace(runtime, 'shutdown:\n    return status;', '    return 0;')
    if 'nul-tokens' in options:
        begin=runtime.index('typedef struct{const char *p;unsigned n;} Span;')
        headers=('static Move resolve_move(',
                 'static __attribute__((noinline)) Move resolve_move(')
        if sum(runtime.count(header) for header in headers)!=1:
            raise ValueError('one exact move resolver boundary required')
        end=runtime.index(next(header for header in headers if header in runtime),begin)
        runtime=runtime[:begin]+'''/* The input thread owns this mutable line until command dispatch finishes.
 * Numeric lookahead leaves an unrecognized key untouched before tokenization.
 * This candidate deliberately supports the measured DEV=0 shipping interface.
 */
#if DEV
#error NUL-token structural candidate requires DEV=0
#endif
typedef char *Span;
static Span scan(char **cursor){
    char *s=*cursor;
    while(*s&&(unsigned char)*s<=32)s++;
    char *first=s;
    while(*s&&(unsigned char)*s>32)s++;
    if(*s)*s++=0;
    *cursor=s;return first;
}
static int word(Span token,const char *name){
    while(*token&&*token==*name)token++,name++;
    return *token==*name;
}
static uint64_t number(Span token){
    uint64_t n=0;
    while(*token){
        unsigned digit=(unsigned)(*token++-'0');
        if(digit>9||n>(uint64_t)LLONG_MAX/10||
           (n==(uint64_t)LLONG_MAX/10&&digit>LLONG_MAX%10))return 0;
        n=n*10+digit;
    }
    return n;
}
static uint64_t amount(char **cursor){
    char *next=*cursor;
    while(*next&&(unsigned char)*next<=32)next++;
    if(*next&&(unsigned)(*next-'0')>9)return 0;
    return number(scan(cursor));
}
'''+runtime[end:]
        runtime=replace(runtime,'return token.n&&resolve_move(b,token,child);',
            'return *token&&resolve_move(b,token,child);')
        runtime=replace(runtime,'resolve_move(b,(Span){0,0},&child)',
            'resolve_move(b,0,&child)')
        runtime=runtime.replace('if(token.n)', 'if(token&&*token)')
        runtime=runtime.replace('(Span){token.p+1,token.n-1}', 'token+1')
        runtime=runtime.replace('(token=scan(&cursor)).n', '*(token=scan(&cursor))')
        runtime=runtime.replace('token.n', '(*token)').replace('token.p', 'token')
        runtime=runtime.replace('scan(&cursor).n', '*scan(&cursor)')
        runtime=runtime.replace('const char *cursor=input;', 'char *cursor=input;')
        runtime=runtime.replace('const char *cursor=s;', 'char *cursor=s;')
        runtime=runtime.replace('const char *cursor=line;', 'char *cursor=line;')
    if 'rodata-first' in options:
        linker = replace(linker,
            '    .text : { *(.text .text.*) } :image\n    .rodata : { *(.rodata .rodata.*) } :image',
            '    .rodata : { *(.rodata .rodata.*) } :image\n    .text : { *(.text .text.*) } :image')
    if 'text-name-order' in options:
        linker = replace(linker, '*(.text .text.*)', '*(.text) *(SORT_BY_NAME(.text.*))')
    if 'rodata-name-order' in options:
        linker = replace(linker, '*(.rodata .rodata.*)', '*(.rodata) *(SORT_BY_NAME(.rodata.*))')
    result.update({'runtime.c': runtime.encode(), 'start.S': start.encode(), 'image.ld': linker.encode()})
    return result
