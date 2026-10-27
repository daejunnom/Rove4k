"""Independent runtime representation candidates for the BSS D prototype.

These are source-only transforms, not production selection or admission.  The
caller owns compilation, whole-file costing and runtime comparison.  The input
is the existing DEV=0 NUL-token runtime after the kernel-owned TT transform;
the unchanged producer still supplies the DEV diagnostic implementation.
"""
from __future__ import annotations

import re


VARIANTS = ("static-stacks", "static-input", "numeric-scan", "command-table")


def _replace(text: str, before: str, after: str, role: str) -> str:
    if text.count(before) != 1:
        raise ValueError(f"runtime size candidate requires unique {role}")
    return text.replace(before, after, 1)


def _section(text: str, begin: str, end: str, role: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f"runtime size candidate requires unique {role} boundaries")
    first, last = text.index(begin), text.index(end)
    if last <= first:
        raise ValueError(f"runtime size candidate requires ordered {role} boundaries")
    return text[first:last]


def _static_stacks(runtime: str) -> str:
    # The TT has already moved to the ELF's final NOBITS segment.  Stacks are
    # therefore the last allocate caller; removing just one earlier caller
    # would not remove the mmap implementation.  Keep the inaccessible page,
    # the usable 1 MiB, child stack alignment and clone failure handling.
    if "Entry *table;" in runtime or runtime.count("allocate(") != 2:
        raise ValueError("static stacks require the kernel-owned TT and one allocation site")
    runtime = _replace(runtime, "Worker workers[WORKERS];\n",
        "/* Process-lifetime stacks; each row begins with its own guard page. */\n"
        "static _Alignas(4096) char worker_stacks[WORKERS][1048576+4096];\n"
        "Worker workers[WORKERS];\n", "worker storage")
    runtime = _replace(runtime,
        "        char *stack=allocate(1048576+4096);if(!stack)abort();\n",
        "        char *stack=worker_stacks[created];\n", "last stack allocation")
    allocator = _section(runtime,
        "static __attribute__((noinline)) void *allocate(size_t n)",
        "static void futex_wait(", "last allocator")
    return _replace(runtime, allocator, "", "last allocator")


def _static_input(runtime: str) -> str:
    # Only the input owner enters set_position and read_line, after wait() has
    # released the previous job.  The line and transaction history are live
    # simultaneously: retain distinct arrays, and commit history only after
    # every replayed move succeeds.
    runtime = _replace(runtime, "    int created=0;char line[32768];\n",
        "    int created=0;static char line[32768];\n", "input line storage")
    return _replace(runtime, "    Board b,c;uint64_t keys[HISTORY];int n=1;\n",
        "    Board b,c;static uint64_t keys[HISTORY];int n=1;\n",
        "transaction history storage")


NUMERIC = r'''static uint64_t amount(char **cursor){
    char *s=*cursor;
    while(*s&&(unsigned char)*s<=32)s++;
    if(*s&&(unsigned)(*s-'0')>9)return 0;
    uint64_t n=0;unsigned bad=0;
    while(*s&&(unsigned char)*s>32){
        unsigned digit=(unsigned)(*s++-'0');
        bad|=digit>9||n>(uint64_t)LLONG_MAX/10||
             (n==(uint64_t)LLONG_MAX/10&&digit>LLONG_MAX%10);
        n=n*10+digit;
    }
    if(*s)*s++=0;
    *cursor=s;return bad?0:n;
}
'''


def _numeric_scan(runtime: str) -> str:
    # The original amount peeks, scan re-reads whitespace and the token, and
    # number reads the token a third time.  This owner consumes a numeric token
    # once.  A non-digit lookahead leaves the original cursor untouched.  A bad
    # numeric token is consumed in full, exactly like scan-before-number.
    # Arithmetic is unsigned even after overflow/invalidity, and bad is sticky.
    before = _section(runtime, "static uint64_t number(Span token){\n",
        "static Move resolve_move(", "numeric token owner")
    return _replace(runtime, before, NUMERIC, "numeric token owner")


COMMANDS = r'''enum {
    D_POSITION=1,D_GO,D_UCI,D_READY,D_QUIT,D_STARTPOS,D_MOVES,
    D_WTIME,D_WINC,D_BTIME,D_BINC
};
static int command_kind(Span token){
    const char *name="position\0go\0uci\0isready\0quit\0startpos\0moves\0wtime\0winc\0btime\0binc\0";
    for(int kind=1;*name;kind++){
        if(word(token,name))return kind;
        while(*name++);
    }
    return 0;
}
'''


def _command_table(runtime: str) -> str:
    # One exact keyword dictionary serves command dispatch, position grammar
    # and the active side's clock grammar.  The terminal double NUL keeps the
    # table traversal inside the string, including unknown/empty input.
    runtime = _replace(runtime, "static int word(Span token,const char *name){\n"
        "    while(*token&&*token==*name)token++,name++;\n"
        "    return *token==*name;\n}\n",
        "static int word(Span token,const char *name){\n"
        "    while(*token&&*token==*name)token++,name++;\n"
        "    return *token==*name;\n}\n" + COMMANDS, "exact keyword owner")
    runtime = _replace(runtime, '    if(word(token,"startpos"))start(&b);\n',
        '    if(command_kind(token)==D_STARTPOS)start(&b);\n', "position start keyword")
    runtime = _replace(runtime,
        '    {token=scan(&cursor);if((*token)&&!word(token,"moves"))return;}\n',
        '    {token=scan(&cursor);if((*token)&&command_kind(token)!=D_MOVES)return;}\n',
        "position moves keyword")
    runtime = _replace(runtime,
        '        if(token[0]==(position.s==1?\'w\':\'b\')&&(word(token+1,"time")||word(token+1,"inc"))){\n'
        '            uint64_t n=amount(&cursor);\n'
        "            if(token[1]=='t'){clock=n;present=1;}else inc=n;\n"
        "        }\n",
        "        int key=command_kind(token)-(position.s==1?D_WTIME:D_BTIME);\n"
        "        if((unsigned)key<2){\n"
        "            uint64_t n=amount(&cursor);\n"
        "            if(!key){clock=n;present=1;}else inc=n;\n"
        "        }\n", "active-side clock keywords")
    return _replace(runtime,
        '        char *cursor=line;Span command=scan(&cursor);\n'
        '        if(word(command,"position")){wait();set_position((char *)cursor);}\n'
        '        else if(word(command,"go"))go((char *)cursor);\n'
        '        else if(*scan(&cursor))continue;\n'
        '        else if(word(command,"uci")){output_counted("uciok\\n",6);}\n'
        '        else if(word(command,"isready")){output_counted("readyok\\n",8);}\n'
        '        else if(word(command,"quit"))break;\n',
        '        char *cursor=line;int command=command_kind(scan(&cursor));\n'
        '        if(command==D_POSITION){wait();set_position(cursor);}\n'
        '        else if(command==D_GO)go(cursor);\n'
        '        else if(*scan(&cursor))continue;\n'
        '        else if(command==D_UCI){output_counted("uciok\\n",6);}\n'
        '        else if(command==D_READY){output_counted("readyok\\n",8);}\n'
        '        else if(command==D_QUIT)break;\n', "command dispatch")


_TRANSFORMS = dict(zip(VARIANTS,
    (_static_stacks, _static_input, _numeric_scan, _command_table)))


def transform(runtime: str, variants: tuple[str, ...]) -> str:
    """Apply only explicitly selected independent candidates, in caller order."""
    if not isinstance(runtime, str) or not isinstance(variants, tuple):
        raise TypeError("runtime text and tuple of candidate names required")
    if len(set(variants)) != len(variants) or any(v not in _TRANSFORMS for v in variants):
        raise ValueError("unknown or repeated runtime size candidate")
    if variants and "#error NUL-token structural candidate requires DEV=0\n" not in runtime:
        raise ValueError("runtime size candidates require the existing DEV=0 NUL-token frontend")
    result = runtime
    for variant in variants:
        result = _TRANSFORMS[variant](result)
    return result


def parser_probe(runtime: str) -> str:
    """Render a small C differential probe; this function executes no process.

    The two parser implementations are extracted from the actual generated C,
    including the original token mutation and missing-value lookahead.  A caller
    may compile/run this on its authorized host with ASan/UBSan.  It allocates no
    engine, worker or transposition table and has a finite deterministic corpus.
    """
    changed = transform(runtime, ("numeric-scan", "command-table"))

    def names(source: str, prefix: str) -> str:
        for name in ("scan", "word", "number", "amount", "command_kind"):
            source = re.sub(r"\b" + name + r"\b", prefix + name, source)
        return source

    def tokens(source: str, prefix: str) -> str:
        text = _section(source, "typedef char *Span;\n", "static Move resolve_move(", "probe tokens")
        return names(text, prefix)

    def clock(source: str, prefix: str) -> str:
        go = _section(source, "static void go(char *s){\n", "#if DEV\nstatic uint64_t perft(", "probe go")
        text = _section(go, "    char *cursor=s;\n", "#if DEV\n    if(!infinite)", "probe clock parser")
        return ("static Clock " + prefix + "clock(char *s,int side){\n"
                "    uint64_t clock=0,inc=0;int present=0;\n" +
                names(text.replace("position.s", "side"), prefix) +
                "    return (Clock){clock,inc,present};\n}\n")

    return (r'''#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DEV 0
typedef struct {uint64_t clock,inc;int present;} Clock;
''' + tokens(runtime, "before_") + tokens(changed, "after_") +
            clock(runtime, "before_") + clock(changed, "after_") + r'''
static unsigned cases;
static void fail(const char *role,const char *s){
    fprintf(stderr,"runtime parser difference: %s, case %u, input ",role,cases);
    for(const unsigned char *p=(const unsigned char *)s;*p;p++)fprintf(stderr,"%02x",*p);
    fputc('\n',stderr);exit(1);
}
static void numeric_case(const char *s){
    char before[32768],after[32768];size_t n=strlen(s)+1;
    if(n>sizeof before)exit(2);
    memcpy(before,s,n);memcpy(after,s,n);char *a=before,*b=after;
    uint64_t x=before_amount(&a),y=after_amount(&b);cases++;
    if(x!=y||a-before!=b-after||memcmp(before,after,n))fail("number/cursor/delimiter",s);
}
static void keyword_case(const char *s){
    int expected=0;
    if(before_word((char *)s,"position"))expected=D_POSITION;
    else if(before_word((char *)s,"go"))expected=D_GO;
    else if(before_word((char *)s,"uci"))expected=D_UCI;
    else if(before_word((char *)s,"isready"))expected=D_READY;
    else if(before_word((char *)s,"quit"))expected=D_QUIT;
    else if(before_word((char *)s,"startpos"))expected=D_STARTPOS;
    else if(before_word((char *)s,"moves"))expected=D_MOVES;
    else if(before_word((char *)s,"wtime"))expected=D_WTIME;
    else if(before_word((char *)s,"winc"))expected=D_WINC;
    else if(before_word((char *)s,"btime"))expected=D_BTIME;
    else if(before_word((char *)s,"binc"))expected=D_BINC;
    cases++;if(after_command_kind((char *)s)!=expected)fail("exact keyword",s);
}
static void clock_case(const char *s){
    char before[32768],after[32768];size_t n=strlen(s)+1;
    if(n>sizeof before)exit(2);
    for(int side=-1;side<=1;side+=2){
        memcpy(before,s,n);memcpy(after,s,n);
        Clock a=before_clock(before,side),b=after_clock(after,side);cases++;
        if(a.clock!=b.clock||a.inc!=b.inc||a.present!=b.present||memcmp(before,after,n))
            fail("clock state/token consumption",s);
    }
}
static uint32_t rng=0xc031f17u;
static uint32_t random_value(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
int main(void){
    const char *fixed[]={""," ","\t\r","0","00","9","10","9223372036854775807",
        "9223372036854775808","18446744073709551615","18446744073709551616",
        "0009223372036854775807","999999999999999999999999999999999999",
        "-1","+1","0x10","12foo"," 123\twinc 7","wtime","btime","winc","binc",
        "position","go","uci","isready","quit","startpos","moves",
        "wtime winc 9","wtime 123foo winc 7","wtime 12 wtime 3 winc 4 binc 9",
        "btime 9223372036854775808 winc 2 wtime 9223372036854775807",
        "wtime btime winc binc wtime 0","wtime 1\200 winc 8"};
    for(size_t i=0;i<sizeof fixed/sizeof *fixed;i++){
        numeric_case(fixed[i]);keyword_case(fixed[i]);clock_case(fixed[i]);
    }
    char s[32768];
    for(unsigned byte=1;byte<256;byte++){
        s[0]='1';s[1]=(char)byte;s[2]='9';s[3]=0;
        numeric_case(s);keyword_case(s);clock_case(s);
        s[0]=(char)byte;numeric_case(s);
    }
    for(size_t i=0;i<sizeof fixed/sizeof *fixed;i++){
        size_t n=strlen(fixed[i]);if(n>32)continue;
        memcpy(s,fixed[i],n+1);
        for(size_t cut=0;cut<=n;cut++){char saved=s[cut];s[cut]=0;keyword_case(s);s[cut]=saved;}
        for(unsigned byte=1;byte<256;byte++){s[n]=(char)byte;s[n+1]=0;keyword_case(s);}
    }
    const unsigned char alphabet[]=" \t\r\n0123456789wtimebncSTARTPOS-+xyz\200\377";
    for(unsigned iteration=0;iteration<20000;iteration++){
        unsigned n=random_value()%128;
        for(unsigned i=0;i<n;i++)s[i]=(char)alphabet[random_value()%(sizeof alphabet-1)];
        s[n]=0;numeric_case(s);keyword_case(s);clock_case(s);
    }
    const char *words[]={"wtime","btime","winc","binc","0","7","1000","-1","+1",
        "9223372036854775807","9223372036854775808","12x","go","position","bogus"};
    for(unsigned iteration=0;iteration<5000;iteration++){
        char *p=s;
        for(unsigned j=0,n=random_value()%24;j<n;j++){
            const char *word=words[random_value()%(sizeof words/sizeof *words)];
            size_t length=strlen(word);memcpy(p,word,length);p+=length;
            *p++=(random_value()&1)?' ':'\t';
        }
        *p=0;clock_case(s);
    }
    memset(s,'9',sizeof s-1);s[sizeof s-1]=0;numeric_case(s);clock_case(s);
    memset(s,'0',sizeof s-1);s[sizeof s-1]=0;numeric_case(s);clock_case(s);
    printf("runtime-parser differential cases=%u\n",cases);return 0;
}
''')
