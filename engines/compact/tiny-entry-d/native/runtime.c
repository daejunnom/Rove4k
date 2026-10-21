#include "tiny.h"

/* Linux x86-64 only. The runtime has no libc, pthread, dynamic loader or TLS.
 * Workers are created before UCI input and persist until quit/EOF. */
static long system_call(long n,long a,long b,long c,long d,long e,long f){
    register long r10 __asm__("r10")=d,r8 __asm__("r8")=e,r9 __asm__("r9")=f;
    long result;
    __asm__ volatile("syscall":"=a"(result):"a"(n),"D"(a),"S"(b),"d"(c),"r"(r10),"r"(r8),"r"(r9):"rcx","r11","memory");
    return result;
}
#define CALL(n,a,b,c,d,e,f) system_call(n,(long)(a),(long)(b),(long)(c),(long)(d),(long)(e),(long)(f))
void *memcpy(void *v,const void *u,size_t n){unsigned char *d=v;const unsigned char *s=u;while(n--)*d++=*s++;return v;}
void *memset(void *v,int c,size_t n){unsigned char *d=v;while(n--)*d++=(unsigned char)c;return v;}
int memcmp(const void *v,const void *u,size_t n){const unsigned char *d=v,*s=u;while(n--){if(*d!=*s)return *d-*s;d++;s++;}return 0;}
#if DEV
size_t strlen(const char *s){const char *p=s;while(*p)p++;return (size_t)(p-s);}
int strcmp(const char *a,const char *b){while(*a&&*a==*b)a++,b++;return (unsigned char)*a-(unsigned char)*b;}
int strncmp(const char *a,const char *b,size_t n){while(n--){if(*a!=*b||!*a)return (unsigned char)*a-(unsigned char)*b;a++;b++;}return 0;}
char *strchr(const char *s,int c){do{if(*s==c)return (char *)s;}while(*s++);return 0;}
char *strstr(const char *s,const char *t){size_t n=strlen(t);for(;*s;s++)if(!strncmp(s,t,n))return (char *)s;return !n?(char *)s:0;}
char *strtok_r(char *s,const char *separators,char **save){
    if(!s)s=*save;
    while(*s&&strchr(separators,*s))s++;
    if(!*s){*save=s;return 0;}
    char *first=s;while(*s&&!strchr(separators,*s))s++;
    if(*s)*s++=0;
    *save=s;return first;
}
#endif
#if DEV
int tiny_errno;
long strtol(const char *s,char **end,int base){
    const char *begin=s;long n=0;int sign=1;
    if(base!=10){tiny_errno=22;*end=(char *)s;return 0;}
    if(*s=='-'||*s=='+'){if(*s=='-')sign=-1;s++;}
    const char *digits=s;
    while(*s>='0'&&*s<='9'){
        int d=*s++-'0';if(n>(LONG_MAX-d)/10){tiny_errno=34;*end=(char *)s;return 0;}n=n*10+d;
    }
    *end=(char *)(s==digits?begin:s);return n*sign;
}
#endif
_Noreturn void abort(void){CALL(231,2,0,0,0,0,0);__builtin_unreachable();}
static void *allocate(size_t n){long p=CALL(9,0,n,3,0x22,-1,0);if((unsigned long)p>=(unsigned long)-4095)return 0;return (void *)p;}
static void futex_wait(atomic_int *address,int value,int private){CALL(202,address,private?128:0,value,0,0,0);}
static void wake(atomic_int *address){CALL(202,address,129,INT_MAX,0,0,0);}
extern long spawn(void (*)(void *),void *,void *,int *);

Entry *table;
Worker workers[WORKERS];
atomic_int stopped;
#if DEV
atomic_uint_fast64_t searched;
uint64_t limit;
int max_depth;
#endif
uint64_t deadline,game_keys[HISTORY];
int game_length;
Board position;
static atomic_int epoch,pending,quitting,ids[WORKERS];
static Move fallback;

uint64_t now(void){long t[2];if(CALL(228,1,t,0,0,0,0))abort();return (uint64_t)t[0]*1000+(uint64_t)t[1]/1000000;}
static void output(const char *s){size_t n=0;while(s[n])n++;while(n){long z=CALL(1,1,s,n,0,0,0);if(z==-4)continue;if(z<=0)abort();s+=z;n-=(size_t)z;}}
static void text(Move m,char *s){
    if(!m){memcpy(s,"0000",5);return;}
    s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;
}
static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
typedef struct{const char *p;unsigned n;} Span;
static Span scan(const char **cursor){
    while(**cursor&&(unsigned char)**cursor<=32)++*cursor;
    const char *first=*cursor;
    while(**cursor&&(unsigned char)**cursor>32)++*cursor;
    return (Span){first,(unsigned)(*cursor-first)};
}
static int word(Span token,const char *name){
    for(unsigned i=0;i<token.n;i++)if(!name[i]||token.p[i]!=name[i])return 0;
    return !name[token.n];
}
static uint64_t number(Span token){
    uint64_t n=0;
    for(unsigned i=0;i<token.n;i++){
        unsigned d=(unsigned)(token.p[i]-'0');
        if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;
        n=n*10+d;
    }
    return n;
}
static uint64_t amount(const char **cursor){
    const char *saved=*cursor;Span token=scan(cursor);
    /* A missing value must not consume the following recognized key. A
     * nonnumeric token is seen again as an ordinary key/unknown token. */
    if(token.n&&(unsigned)(token.p[0]-'0')>9)*cursor=saved;
    return number(token);
}
static int parse_apply(const Board *b,Span token,Board *child){
    if(token.n!=4&&token.n!=5)return 0;
    unsigned a=(unsigned)(token.p[0]-'a'),r=(unsigned)(token.p[1]-'1');
    unsigned c=(unsigned)(token.p[2]-'a'),s=(unsigned)(token.p[3]-'1');
    if((a|r|c|s)>7)return 0;
    unsigned promotion=0;
    if(token.n==5){
        for(promotion=2;promotion<6&&"  nbrq"[promotion]!=token.p[4];promotion++);
        if(promotion==6)return 0;
    }
    Move move=MOVE(a+(r<<4),c+(s<<4),promotion),list[MOVES];
    int count=gen(b,list);
    for(int i=0;i<count;i++)if((list[i]&~8u)==move)return make(b,list[i],child);
    return 0;
}

#if DEV
static char *decimal(char *s,uint64_t n){char digits[24];int count=0;do{digits[count++]='0'+n%10;n/=10;}while(n);while(count)*s++=digits[--count];*s=0;return s;}
static char *signed_decimal(char *s,int n){if(n<0)*s++='-',n=-n;return decimal(s,(unsigned)n);}
static char *append(char *s,const char *t){size_t n=strlen(t);memcpy(s,t,n+1);return s+n;}
#endif
static void result(void){
    Worker *w=workers;for(int i=1;i<WORKERS;i++)if(workers[i].depth>w->depth)w=workers+i;
    Move best=w->best?w->best:fallback;char move[6],reply[256],*s=reply;text(best,move);
#if DEV
    s=append(s,"info depth ");s=decimal(s,w->depth);s=append(s," score ");
    int score=w->score;
    if(abs(score)>=MATE-PLY){s=append(s,"mate ");score=score>0?(MATE-score+1)/2:-(MATE+score+1)/2;}else s=append(s,"cp ");
    s=signed_decimal(s,score);s=append(s," nodes ");s=decimal(s,atomic_load(&searched));
    if(best){s=append(s," pv ");s=append(s,move);}s=append(s,"\n");
#endif
    memcpy(s,"bestmove ",9);s+=9;size_t n=4+!!PROMO(best);memcpy(s,move,n);s[n]='\n';s[n+1]=0;output(reply);
}
static void work(void *p){
    Worker *w=p;int seen=0;
    atomic_fetch_sub_explicit(&pending,1,memory_order_release);wake(&pending);
    for(;;){
        int current=atomic_load_explicit(&epoch,memory_order_acquire);
        if(atomic_load_explicit(&quitting,memory_order_relaxed))return;
        if(current==seen){futex_wait(&epoch,seen,1);continue;}
        seen=current;w->best=0;think(w,&position);
        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==2){
            result();atomic_store_explicit(&pending,0,memory_order_release);wake(&pending);
        }
    }
}
/* pending counts startup arrivals, then workers plus an output reservation.
 * Only zero releases storage after the complete bestmove has been written. */
static void wait(void){
    atomic_store_explicit(&stopped,1,memory_order_relaxed);
    int count;while((count=atomic_load_explicit(&pending,memory_order_acquire)))futex_wait(&pending,count,1);
}
#if DEV
static void clear(void){memset(table,0,((size_t)1<<TT_BITS)*sizeof *table);}
#endif
static void set_position(char *input){
    const char *cursor=input;Span token=scan(&cursor);
    Board b,c;uint64_t keys[HISTORY];int n=1;
#if DEV
    int have_moves=0;
#endif
    if(word(token,"startpos"))start(&b);
#if DEV
    else if(word(token,"fen")){
        const char *begin=cursor,*tail=cursor;Span marker=scan(&begin);
        begin=marker.p;
        while((marker=scan(&tail)).n&&!word(marker,"moves"));
        if(marker.n){*(char *)marker.p=0;have_moves=1;}
        if(!fen(&b,begin))return;
        cursor=tail;
    }
#endif
    else return;
#if DEV
    if(!have_moves)
#endif
    {token=scan(&cursor);if(token.n&&!word(token,"moves"))return;}
    keys[0]=b.h;
    while((token=scan(&cursor)).n){
        if(n==HISTORY||!parse_apply(&b,token,&c))return;
        b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}


static int read_line(char *s){
    static char bytes[4096];static int at,length;int n=0,bad=0;
    for(;;){
        if(at==length){long got=CALL(0,0,bytes,sizeof bytes,0,0,0);if(got==-4)continue;if(got<0)abort();at=0;length=(int)got;if(!got){s[n]=0;return n?!bad:-1;}}
        int c=(unsigned char)bytes[at++];if(c=='\n')break;
        if(!c||n==32767)bad=1;else s[n++]=(char)c;
    }
    s[n]=0;return !bad;
}
static void go(char *s){
#if DEV
    wait();deadline=UINT64_MAX;
#else
    wait();
#endif
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
#if DEV
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;
#else
    uint64_t clock=0,inc=0,budget=0;int present=0;
#endif
    const char *cursor=s;
    for(Span token;(token=scan(&cursor)).n;){
        if(word(token,"wtime")||word(token,"btime")){
            int side=*token.p=='w'?1:-1;uint64_t n=amount(&cursor);
            if(side==position.s){clock=n;present=1;}
        }
        else if(word(token,"winc")||word(token,"binc")){
            int side=*token.p=='w'?1:-1;uint64_t n=amount(&cursor);
            if(side==position.s)inc=n;
        }
#if DEV
        else if(word(token,"infinite"))infinite=1;
        else if(word(token,"depth")){uint64_t n=amount(&cursor);if(n&&n<PLY-1)max_depth=(int)n;}
        else if(word(token,"nodes"))limit=amount(&cursor);
        else if(word(token,"movetime")){budget=amount(&cursor);if(!budget)budget=1;}
#endif
    }
#if DEV
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
#else
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
#endif
    fallback=first(&position);atomic_store_explicit(&stopped,0,memory_order_relaxed);
    atomic_store_explicit(&pending,WORKERS+1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);
}
#if DEV
static uint64_t perft(const Board *b,int d){if(!d)return 1;uint64_t total=0;Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))total+=perft(&c,d-1);return total;}
static int drawn(void){int n=0;for(int i=0;i<game_length;i++)n+=game_keys[i]==position.h;return position.half>=100||n>=3||dead(&position);}
static void stats(void){
    const char *names[]={"workers","total_threads","nodes","completed_depth","pvs","qs","tt_hits","history_updates","continuation_updates","correction_updates","correction_uses","ply_aborts"};
    uint64_t data[12]={WORKERS,WORKERS+1,atomic_load(&searched)};
    for(int i=0;i<WORKERS;i++){
        Worker *w=workers+i;if(w->depth>(int)data[3])data[3]=w->depth;
        data[4]+=w->pvs;data[5]+=w->qs;data[6]+=w->hits;data[7]+=w->hist_updates;data[8]+=w->cont_updates;data[9]+=w->corr_updates;data[10]+=w->corr_uses;data[11]+=w->ply_aborts;
    }
    char reply[1024],*s=reply;*s++='{';
    for(int i=0;i<12;i++){if(i)*s++=',';*s++='"';s=append(s,names[i]);*s++='"';*s++=':';s=decimal(s,data[i]);}
    s=append(s,"}\n");output(reply);
}
#endif
int main(void){
    int created=0,status=0;char line[32768];
    table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;start(&position);game_keys[0]=position.h;game_length=1;
    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);
    for(;created<WORKERS;created++){
        workers[created].id=created;
        /* One inaccessible guard page precedes each private 1 MiB stack. */
        char *stack=allocate(1048576+4096);if(!stack){status=2;break;}
        if(CALL(10,stack,4096,0,0,0,0)||spawn(work,workers+created,stack+1048576+4096,(int *)(ids+created))<0){status=2;break;}
    }
    if(status)goto shutdown;
    wait();
    for(;;){
        int valid=read_line(line);if(valid<0)break;if(!valid)continue;
#if !DEV
        const char *cursor=line;Span command=scan(&cursor);
        if(word(command,"position")){wait();set_position((char *)cursor);}
        else if(word(command,"go"))go((char *)cursor);
        else if(scan(&cursor).n)continue;
        else if(word(command,"uci")){output("uciok\n");}
        else if(word(command,"isready")){output("readyok\n");}
        else if(word(command,"quit"))break;
#else
        size_t n=strlen(line);while(n&&(line[n-1]=='\r'||line[n-1]==' '||line[n-1]=='\t'))line[--n]=0;
        if(!strcmp(line,"uci"))output("id name Rove4k D syscall\nuciok\n");
        else if(!strcmp(line,"isready"))output("readyok\n");
        else if(!strcmp(line,"quit"))break;
        else if(!strcmp(line,"stop"))wait();
        else if(!strcmp(line,"ucinewgame")){wait();clear();}
        else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}
        else if(!strcmp(line,"go")||!strncmp(line,"go ",3))go(line+2);
#if DEV
        else if(!strncmp(line,"perft ",6)){wait();uint64_t d=number((Span){line+6,(unsigned)strlen(line+6)});if(d<=8){char reply[80],*s=append(reply,"perft ");s=decimal(s,d);*s++=' ';s=decimal(s,perft(&position,(int)d));append(s,"\n");output(reply);}}
        else if(!strcmp(line,"legal")){wait();Move list[MOVES];Board b;int count=gen(&position,list);char reply[MOVES*7+8],*s=append(reply,"legal");for(int i=0;i<count;i++)if(make(&position,list[i],&b)){char name[6];text(list[i],name);*s++=' ';s=append(s,name);}append(s,"\n");output(reply);}
        else if(!strcmp(line,"eval")){wait();char reply[64],*s=append(reply,"eval ");s=signed_decimal(s,position.v*position.s);append(s,"\n");output(reply);}
        else if(!strcmp(line,"state")){wait();char reply[256],*s=append(reply,"{\"hash\":\"");for(int shift=60;shift>=0;shift-=4)*s++="0123456789abcdef"[(position.h>>shift)&15];s=append(s,"\",\"halfmove\":");s=decimal(s,position.half);s=append(s,",\"eval\":");s=signed_decimal(s,position.v*position.s);s=append(s,",\"draw\":");s=append(s,drawn()?"true":"false");s=append(s,",\"invariant\":");s=append(s,verify_board(&position)?"true":"false");append(s,"}\n");output(reply);}
        else if(!strcmp(line,"verify")){wait();Move list[MOVES];Board b;int good=verify_board(&position),count=gen(&position,list),tested=1;for(int i=0;i<count;i++)if(make(&position,list[i],&b)){good&=verify_board(&b);tested++;}char reply[80],*s=append(reply,good?"verify pass positions ":"verify fail positions ");s=decimal(s,tested);append(s,"\n");output(reply);}
        else if(!strcmp(line,"stats")){wait();stats();}
#endif
#endif
    }
    wait();
shutdown:
    atomic_store_explicit(&quitting,1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake(&epoch);
    for(int i=0;i<created;i++){int id;while((id=atomic_load_explicit(ids+i,memory_order_acquire)))futex_wait(ids+i,id,0);}
    return status;
}
