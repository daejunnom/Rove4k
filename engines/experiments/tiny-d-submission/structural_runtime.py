"""Pure, finite structural variants for the closed D shipping runtime.

The input is the readable runtime after no-TID ownership and square-successor
preparation; other files may carry independent board/search changes. Only
runtime.c changes. This module does not build, run, package, qualify or publish.
The measured/validated scope is DEV=0. Original DEV branches are retained where
shipping output or token representation diverges, without claiming DEV support.

Contracts:
* Notation inversion matches the complete existing formatter output against a
  gen() witness before the same make() call. All promotions and internal move
  flags survive; no move legality is inferred from observed samples.
* The shared resolver retains first-legal order, rejects an empty parse token,
  and fails on the first matching but illegal input move as before.
* Decimal variants preserve the inclusive 0..LLONG_MAX domain and return zero
  for malformed/overflowing tokens. Clock factoring requires Board.s in {-1,1};
  missing values must leave the next recognized key available to the parser.
* Direct/counted output preserves bestmove bytes, partial-write/EINTR handling,
  and the existing publication reservation. Worker/input/exit policy is intact.

Pointer tokens and other selectors preserve measured rejected alternatives;
selection still requires whole-file cost and the relevant behavior checks.
"""
from hashlib import sha256
import re

BASELINE_RUNTIME_SHA256 = "4ed5d28d3bdec003dc556ce3265150ab680af511481c22839c86e1cd05e9c81e"
BEST = (
    "notation-inverse", "direct-output", "counted-output", "number-limit",
    "keys-own", "noinline-allocate", "shared-resolver",
)
_NOINLINE = (
    "go", "set_position", "parse_apply", "number", "amount", "text",
    "result", "allocate", "read_line", "scan", "word", "first",
)
OPTIONS = (
    "notation-inverse", "notation-length", "direct-output", "counted-output",
    "number-limit", "number-overflow", "keys-own", "keys-family", "keys-char",
    "shared-resolver", "resolver-noinline", "pointer-tokens",
) + tuple("noinline-" + name for name in _NOINLINE)

def _replace_exact(source,old,new):
    if source.count(old) != 1:
        raise ValueError("runtime spelling is not unique: " + old[:100])
    return source.replace(old,new)

def _function(source,name):
    m=re.search(r'^static [^{\n]*\b'+re.escape(name)+r'\([^{}\n]*\)\s*\{',source,re.M)
    if not m:
        raise ValueError("runtime function absent: " + name)
    start=m.start();cur=m.end();depth=1
    # Closed selected bodies have no braces inside literals/comments. The
    # header excludes braces so one-line loops and compound literals cannot
    # be mistaken for the function's opening brace.
    while depth:
        if cur >= len(source):
            raise ValueError("unbalanced runtime function: " + name)
        if source[cur]=='{':depth+=1
        if source[cur]=='}':depth-=1
        cur+=1
    return source[start:cur]

def _output_and_tokens(files, *, direct=False, counted=False, pointer=False):
    files=dict(files);s=files['runtime.c'].decode()
    if direct:
        old=_function(s,'result')
        new='''static void result(void){
    Worker *winner=workers;
    for(int index=1;index<WORKERS;index++)if(workers[index].depth>winner->depth)winner=workers+index;
    Move best=winner->best?winner->best:fallback;
    char reply[16]="bestmove ";
    text(best,reply+9);
    unsigned count=13+!!PROMO(best);
    reply[count]='\\n';reply[count+1]=0;
    output(reply);
}'''
        s=_replace_exact(s,old,'#if DEV\n'+old+'\n#else\n'+new+'\n#endif')
    if counted:
        old=_function(s,'output')
        new='''static void output_counted(const char *s,size_t n){while(n){long z=Dsc3(1,1,(long)s,(long)n);if(z==-4)continue;if(z<=0)abort();s+=z;n-=(size_t)z;}}
#if DEV
static void output(const char *s){size_t n=0;while(s[n])n++;output_counted(s,n);}
#endif'''
        s=_replace_exact(s,old,new)
        if direct:
            s=_replace_exact(s,"reply[count]='\\n';reply[count+1]=0;\n    output(reply);", "reply[count]='\\n';\n    output_counted(reply,count+1);")
        else:
            old_result=_function(s,'result')
            new_result=old_result.replace('output(reply);','output_counted(reply,14+!!PROMO(best));')
            s=_replace_exact(s,old_result,'#if DEV\n'+old_result+'\n#else\n'+new_result+'\n#endif')
        s=_replace_exact(s,'else if(word(command,"uci")){output("uciok\\n");}','else if(word(command,"uci")){output_counted("uciok\\n",6);}')
        s=_replace_exact(s,'else if(word(command,"isready")){output("readyok\\n");}','else if(word(command,"isready")){output_counted("readyok\\n",8);}')
    if pointer:
        a=s.index('typedef struct{const char *p;unsigned n;} Span;')
        b=s.index('\n#if DEV\nstatic char *decimal',a)
        old=s[a:b]
        new='''/* Shipping tokens own their input line; split separators in place. */
static const char *scan(const char **cursor){
    while(**cursor&&(unsigned char)**cursor<=32)++*cursor;
    const char *first=*cursor;
    while(**cursor&&(unsigned char)**cursor>32)++*cursor;
    if(**cursor)*(char *)(*cursor)++=0;
    return first;
}
static int word(const char *token,const char *name){
    while(*token&&*token==*name)token++,name++;
    return *token==*name;
}
static uint64_t number(const char *token){
    uint64_t n=0;
    for(;*token;token++){
        unsigned digit=(unsigned)(*token-'0');
        if(digit>9||n>((uint64_t)LLONG_MAX-digit)/10)return 0;
        n=n*10+digit;
    }
    return n;
}
static uint64_t amount(const char **cursor){
    const char *look=*cursor;
    while(*look&&(unsigned char)*look<=32)look++;
    /* Look ahead before splitting: a missing value retains the next key. */
    if((unsigned)(*look-'0')>9)return 0;
    return number(scan(cursor));
}
static int parse_apply(const Board *b,const char *token,Board *child){
    unsigned length=0;while(token[length])length++;
    if(length!=4&&length!=5)return 0;
    unsigned file_from=(unsigned)(token[0]-'a'),rank_from=(unsigned)(token[1]-'1');
    unsigned file_to=(unsigned)(token[2]-'a'),rank_to=(unsigned)(token[3]-'1');
    if((file_from|rank_from|file_to|rank_to)>7)return 0;
    unsigned promotion=0;
    if(length==5){
        for(promotion=2;promotion<6&&"  nbrq"[promotion]!=token[4];promotion++);
        if(promotion==6)return 0;
    }
    Move move=MOVE(file_from+(rank_from<<4),file_to+(rank_to<<4),promotion),list[MOVES];
    int count=gen(b,list);
    for(int index=0;index<count;index++)if((list[index]&~8u)==move)return make(b,list[index],child);
    return 0;
}
'''
        s=s[:a]+'#if DEV\n'+old+'\n#else\n'+new+'#endif\n'+s[b:]
        old=_function(s,'set_position')
        new='''static void set_position(char *input){
    const char *cursor=input,*token=scan(&cursor);
    Board b,c;uint64_t keys[HISTORY];int n=1;
    if(word(token,"startpos"))start(&b);else return;
    token=scan(&cursor);if(*token&&!word(token,"moves"))return;
    keys[0]=b.h;
    while(*(token=scan(&cursor))){
        if(n==HISTORY||!parse_apply(&b,token,&c))return;
        b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}'''
        s=_replace_exact(s,old,'#if DEV\n'+old+'\n#else\n'+new+'\n#endif')
        old=_function(s,'go')
        new='''static void go(char *s){
    wait();
    uint64_t clock=0,inc=0,budget=0;int present=0;
    const char *cursor=s,*token;
    while(*(token=scan(&cursor))){
        if(word(token,"wtime")||word(token,"btime")||word(token,"winc")||word(token,"binc")){
            int side=*token=='w'?1:-1;uint64_t n=amount(&cursor);
            if(side==position.s){if(token[1]=='t'){clock=n;present=1;}else inc=n;}
        }
    }
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
    fallback=first(&position);atomic_store_explicit(&stopped,0,memory_order_relaxed);
    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);
}'''
        s=_replace_exact(s,old,'#if DEV\n'+old+'\n#else\n'+new+'\n#endif')
        s=_replace_exact(s,'const char *cursor=line;Span command=scan(&cursor);','const char *cursor=line,*command=scan(&cursor);')
        s=_replace_exact(s,'else if(scan(&cursor).n)continue;','else if(*scan(&cursor))continue;')
    files['runtime.c']=s.encode();return files

def _scalar(files,kind):
    files=dict(files);s=files['runtime.c'].decode()
    old='if(word(token,"wtime")||word(token,"btime")||word(token,"winc")||word(token,"binc")){'
    if kind=='keys-family':
        new='if((token.p[0]==\'w\'||token.p[0]==\'b\')&&(word((Span){token.p+1,token.n-1},"time")||word((Span){token.p+1,token.n-1},"inc"))){'
        s=_replace_exact(s,old,new)
    elif kind=='keys-own':
        new='if(token.p[0]==(position.s==1?\'w\':\'b\')&&(word((Span){token.p+1,token.n-1},"time")||word((Span){token.p+1,token.n-1},"inc"))){'
        s=_replace_exact(s,old,new)
        s=_replace_exact(s,"int side=*token.p=='w'?1:-1;uint64_t n=amount(&cursor);\n            if(side==position.s){if(token.p[1]=='t'){clock=n;present=1;}else inc=n;}","uint64_t n=amount(&cursor);\n            if(token.p[1]=='t'){clock=n;present=1;}else inc=n;")
    elif kind=='keys-char':
        new='if((token.p[0]==\'w\'||token.p[0]==\'b\')&&((token.n==5&&token.p[1]==\'t\'&&token.p[2]==\'i\'&&token.p[3]==\'m\'&&token.p[4]==\'e\')||(token.n==4&&token.p[1]==\'i\'&&token.p[2]==\'n\'&&token.p[3]==\'c\'))){'
        s=_replace_exact(s,old,new)
    elif kind=='number-limit':
        s=_replace_exact(s,'if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;','if(d>9||n>(uint64_t)LLONG_MAX/10||(n==(uint64_t)LLONG_MAX/10&&d>LLONG_MAX%10))return 0;')
    elif kind=='number-overflow':
        s=_replace_exact(s,'if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;\n        n=n*10+d;','if(d>9||__builtin_mul_overflow(n,10,&n)||__builtin_add_overflow(n,d,&n)||n>LLONG_MAX)return 0;')
    elif kind.startswith('noinline-'):
        fname=kind.removeprefix('noinline-')
        s,n=re.subn(r'^(static )(?!__attribute__)([^\n]*?\b'+fname+r'\()',r'\1__attribute__((noinline)) \2',s,flags=re.M)
        if n < 1:
            raise ValueError("no eligible noinline function: " + fname)
    else:raise ValueError(kind)
    files['runtime.c']=s.encode();return files

def _notation(files, *, first_length=False):
 files=dict(files);s=files['runtime.c'].decode();old=_function(s,'parse_apply')
 new='''static int parse_apply(const Board *b,Span token,Board *child){
    Move list[MOVES];int count=gen(b,list);char name[6];
    for(int index=0;index<count;index++){
        text(list[index],name);
        if(word(token,name))return make(b,list[index],child);
    }
    return 0;
}'''
 if first_length:new=new.replace('    Move list', '    if(token.n!=4&&token.n!=5)return 0;\n    Move list')
 s=_replace_exact(s,old,new);files['runtime.c']=s.encode();return files

def _resolver(files, *, noinline=False):
 files=dict(files);s=files['runtime.c'].decode();old=_function(s,'first')
 s=_replace_exact(s,old,'')
 old=_function(s,'parse_apply')
 new='''static Move resolve_move(const Board *b,Span token,Board *child){
    Move list[MOVES];int count=gen(b,list);char name[6];
    for(int index=0;index<count;index++){
        if(token.n){text(list[index],name);if(!word(token,name))continue;}
        if(make(b,list[index],child))return list[index];
        if(token.n)return 0;
    }
    return 0;
}
static int parse_apply(const Board *b,Span token,Board *child){return token.n&&resolve_move(b,token,child);}
static Move first(const Board *b){Board child;return resolve_move(b,(Span){0,0},&child);}'''
 if noinline:new=new.replace('static Move resolve_move','static __attribute__((noinline)) Move resolve_move')
 s=_replace_exact(s,old,new);files['runtime.c']=s.encode();return files


def apply(files, options=BEST):
    """Return a new mapping with the selected finite runtime projection.

    Options are an unordered collection. Empty options returns the control.
    Mutually exclusive representations are rejected, never silently dropped.
    This is a closed source projection, not a generic C refactoring parser.
    """
    if not isinstance(files, dict) or not isinstance(files.get("runtime.c"), bytes):
        raise ValueError("named immutable runtime source required")
    if isinstance(options, (str, bytes)):
        raise ValueError("options must be a collection of selectors")
    selected = set(options)
    unknown = selected.difference(OPTIONS)
    if unknown:
        raise ValueError("unknown runtime options: " + repr(sorted(unknown)))
    if not selected:
        return dict(files)
    if sha256(files["runtime.c"]).hexdigest() != BASELINE_RUNTIME_SHA256:
        raise ValueError("closed prepared runtime differs; regenerate from its source chain")
    if len(selected.intersection(("number-limit", "number-overflow"))) > 1:
        raise ValueError("choose one decimal representation")
    if len(selected.intersection(("keys-own", "keys-family", "keys-char"))) > 1:
        raise ValueError("choose one clock-key representation")
    if "notation-length" in selected and "notation-inverse" not in selected:
        raise ValueError("notation-length requires notation-inverse")
    if "resolver-noinline" in selected and "shared-resolver" not in selected:
        raise ValueError("resolver-noinline requires shared-resolver")
    if "shared-resolver" in selected:
        if "notation-inverse" not in selected:
            raise ValueError("shared-resolver requires notation-inverse")
        if "notation-length" in selected:
            raise ValueError("shared-resolver has its own empty-token predicate")
    if "pointer-tokens" in selected and selected.difference(
            ("pointer-tokens", "direct-output", "counted-output")):
        raise ValueError("pointer-token protocol composes only with output selectors")

    result = dict(files)
    if "notation-inverse" in selected:
        result = _notation(result, first_length="notation-length" in selected)
    result = _output_and_tokens(
        result, direct="direct-output" in selected,
        counted="counted-output" in selected, pointer="pointer-tokens" in selected)
    for option in ("number-limit", "number-overflow", "keys-own", "keys-family", "keys-char"):
        if option in selected:
            result = _scalar(result, option)
    if "shared-resolver" in selected:
        result = _resolver(result, noinline="resolver-noinline" in selected)
    for name in _NOINLINE:
        if "noinline-" + name in selected:
            result = _scalar(result, "noinline-" + name)
    return result


def render_helper_probe(before, after):
    """Render the finite Span-helper equivalence C probe; perform no I/O.

    The driver checks numeric boundaries/random tokens, both clock sides and
    missing values, all nonzero valid-coordinate/promotion move witnesses,
    malformed notation and ordered first-legal selection. gen/make are mocks;
    this is not engine/rules/runtime qualification. Compile with ASan+UBSan.
    """
    old = before["runtime.c"].decode()
    new = after["runtime.c"].decode()
    names = ("scan", "word", "number", "amount", "text", "resolve_move",
             "parse_apply", "first")
    for source in (old, new):
        for name in ("scan", "go"):
            matches = re.findall(r"^static [^{\n]*\b" + name + r"\([^{}\n]*\)\s*\{", source, re.M)
            if len(matches) != 1:
                raise ValueError("helper probe requires a single Span-based " + name)
    # The mocked generator emits at most four moves. This proof depends on
    # Move's representation, not the engine's Board layout or list capacity;
    # those remain the responsibility of the full engine/rules checks.
    for line in ("typedef unsigned Move;",
                 "#define FROM(m) ((m)&119)", "#define TO(m) (((m)>>7)&127)",
                 "#define PROMO(m) (((m)>>14)&7)",
                 "#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))"):
        if any(line.encode() not in files["tiny.h"].splitlines() for files in (before, after)):
            raise ValueError("helper probe requires the original Move representation")

    def emit(source, prefix):
        code = "\n".join(_function(source, name) for name in names
                         if re.search(r"^static [^{\n]*\b" + name + r"\(", source, re.M)) + "\n"
        go = _function(source, "go")
        begin = go.index("    const char *cursor=s;")
        end = go.index("#if DEV\n    if(!infinite)", begin)
        code += ("static void parse_clock(char *s,int side,uint64_t out[3]){"
                 "uint64_t clock=0,inc=0,budget=0;int present=0;position.s=side;\n"
                 + go[begin:end] + "out[0]=clock;out[1]=inc;out[2]=present;}\n")
        for name in (*names, "parse_clock"):
            code = re.sub(r"\b" + name + r"\b", prefix + name, code)
        return code

    return (_PROBE_PREFIX + emit(old, "ref_") + emit(new, "new_") + _PROBE_MAIN).encode()

_PROBE_PREFIX = r'''
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define DEV 0
#define MOVES 512
typedef unsigned Move;
#define FROM(m) ((m)&119)
#define TO(m) (((m)>>7)&127)
#define PROMO(m) (((m)>>14)&7)
#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))
typedef struct {const char *p;unsigned n;}Span;
typedef struct {int s;Move witness;}Board;
static Board position;
static Move listed;
static int legal=1,pool_count=-1;
static Move pool[4],selected_legal;
static int gen(const Board *b,Move *out){(void)b;if(pool_count>=0){for(int i=0;i<pool_count;i++)out[i]=pool[i];return pool_count;}out[0]=listed;return 1;}
static int make(const Board *b,Move move,Board *out){*out=*b;out->witness=move;return legal==2?move==selected_legal:legal;}
'''

_PROBE_MAIN = r'''
static uint64_t checks_num,checks_clock,checks_move,checks_first,random_state=918273;
static unsigned rng(void){random_state=random_state*6364136223846793005ULL+1;return random_state>>32;}
static void check_num(const char *s){Span t={s,(unsigned)strlen(s)};if(ref_number(t)!=new_number(t)){fprintf(stderr,"number %s\n",s);exit(1);}checks_num++;}
static void check_clock(char *s){uint64_t a[3],b[3];for(int side=-1;side<=1;side+=2){ref_parse_clock(s,side,a);new_parse_clock(s,side,b);if(memcmp(a,b,sizeof a)){fprintf(stderr,"clock %s side %d\n",s,side);exit(2);}checks_clock++;}}
static void check_move(const char *s){Span t={s,(unsigned)strlen(s)};Board in={1,0},a={1,0},b={1,0};int ar=ref_parse_apply(&in,t,&a),br=new_parse_apply(&in,t,&b);if(ar!=br||(ar&&a.witness!=b.witness)){fprintf(stderr,"move %s witness %u legal %d\n",s,listed,legal);exit(3);}checks_move++;}
static void check_first(void){Board in={1,0};Move a=ref_first(&in),b=new_first(&in);if(a!=b){fprintf(stderr,"first mismatch %u %u\n",a,b);exit(4);}checks_first++;}
int main(void){
 char buffer[512];
 const char *edges[]={"","0","00","1","9","10","922337203685477580","9223372036854775806","9223372036854775807","9223372036854775808","9223372036854775809","18446744073709551615","18446744073709551616","99999999999999999999999999999","-1","+1","1x","x1","01"," 1","1 ","99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999"};
 for(unsigned i=0;i<sizeof(edges)/sizeof(*edges);i++)check_num(edges[i]);
 for(unsigned i=0;i<10000;i++){sprintf(buffer,"%u",i);check_num(buffer);}
 for(unsigned i=0;i<200000;i++){unsigned count=rng()%100;for(unsigned j=0;j<count;j++)buffer[j]="0123456789+-xy"[rng()%14];buffer[count]=0;check_num(buffer);}
 const char *tokens[]={"wtime","btime","winc","binc","0","1","87","9223372036854775807","9223372036854775808","-1","23x","unknown","wtimeX","bincX","infinite","go"};
 for(unsigned i=0;i<65536;i++){unsigned n=i;buffer[0]=0;for(int j=0;j<4;j++){strcat(buffer,tokens[n&15]);n>>=4;strcat(buffer,j%2?"\t":" ");}check_clock(buffer);}
 check_clock("  wtime btime 700 winc binc 9 wtime 500 winc 17  ");
 check_clock("btime winc 7 wtime 1100 wtime 1200 winc 0");
 for(unsigned from=0;from<128;from++)if(!(from&0x88))for(unsigned to=0;to<128;to++)if(!(to&0x88)&&from!=to)for(unsigned promo=0;promo<6;promo++)if(promo!=1)for(unsigned flags=0;flags<=8;flags+=8){
  listed=MOVE(from,to,promo)|flags;ref_text(listed,buffer);legal=1;check_move(buffer);check_first();legal=0;check_move(buffer);check_first();legal=1;
  unsigned len=strlen(buffer);buffer[len]='x';buffer[len+1]=0;check_move(buffer);buffer[len]=0;buffer[0]='!';check_move(buffer);
 }
 listed=MOVE(16,32,0);for(unsigned i=0;i<200000;i++){unsigned count=rng()%8;for(unsigned j=0;j<count;j++)buffer[j]="abcdefgh12345678nbrqABC012xyz"[rng()%28];buffer[count]=0;check_move(buffer);}
 pool_count=0;check_first();pool_count=4;pool[0]=MOVE(16,32,0);pool[1]=MOVE(17,33,0);pool[2]=MOVE(18,34,0);pool[3]=MOVE(19,35,0);legal=0;check_first();legal=1;check_first();legal=2;for(unsigned i=0;i<4;i++){selected_legal=pool[i];check_first();}pool_count=-1;
 printf("{\"numeric_cases\":%llu,\"clock_cases\":%llu,\"notation_cases\":%llu,\"first_cases\":%llu,\"all_equal\":true}\n",(unsigned long long)checks_num,(unsigned long long)checks_clock,(unsigned long long)checks_move,(unsigned long long)checks_first);
 return 0;
}
'''
