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
/* Only kernel-cleared TID joins retain a futex. Job/readiness/completion
 * notifications below are directed to one blocked thread, never the process. */
static void join_wait(atomic_int *address,int value){CALL(202,address,0,value,0,0,0);}
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
static atomic_int epoch,pending,completed,ready,quitting,ids[WORKERS];
static int process_id;
static Move fallback;

/* Linux x86-64 raw ABI: 64 signals, one 8-byte kernel sigset, unlike glibc's
 * 128-byte sigset_t. The raw sigaction is handler/flags/restorer/mask, 32 B.
 * Block before resetting inherited SIG_IGN to DFL, before creating workers.
 * No C signal handler runs and both private signals stay blocked throughout. */
static void signals_init(void){
    uint64_t mask=UINT64_C(0xa00);long action[4]={0};
    if(CALL(14,0,&mask,0,8,0,0)||CALL(13,10,action,0,8,0,0)||CALL(13,12,action,0,8,0,0))abort();
    process_id=(int)CALL(39,0,0,0,0,0,0);if(process_id<=0)abort();
}
static void signal_wait(int signal){
    uint64_t mask=UINT64_C(1)<<(signal-1);long result;
    do{result=CALL(128,&mask,0,0,8,0,0);}while(result==-4);
    if(result!=signal)abort();
}
static void notify(int tid,int signal){
    long result;do{result=CALL(234,process_id,tid,signal,0,0,0);}while(result==-4);
    /* A worker can observe quitting and exit before shutdown fanout reaches
     * its sampled TID. Only that ESRCH is expected; job errors fail closed. */
    if(result&&!(result==-3&&atomic_load_explicit(&quitting,memory_order_relaxed)))abort();
}
static void wake_workers(int count){
    for(int i=0;i<count;i++){
        int tid=atomic_load_explicit(ids+i,memory_order_acquire);
        if(tid)notify(tid,10);
        else if(!atomic_load_explicit(&quitting,memory_order_relaxed))abort();
    }
}

uint64_t now(void){long t[2];if(CALL(228,1,t,0,0,0,0))abort();return (uint64_t)t[0]*1000+(uint64_t)t[1]/1000000;}
static void output(const char *s){size_t n=strlen(s);while(n){long z=CALL(1,1,s,n,0,0,0);if(z==-4)continue;if(z<=0)abort();s+=z;n-=(size_t)z;}}
static void text(Move m,char *s){
    if(!m){memcpy(s,"0000",5);return;}
    s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;
}
static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
static Move parse(const Board *b,const char *s){
    Move list[MOVES];Board c;char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;
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
    memcpy(s,"bestmove ",9);s+=9;size_t n=strlen(move);memcpy(s,move,n);s[n]='\n';s[n+1]=0;output(reply);
}
static void work(void *p){
    Worker *w=p;int seen=0;
    atomic_fetch_add_explicit(&ready,1,memory_order_release);notify(process_id,12);
    for(;;){
        int current=atomic_load_explicit(&epoch,memory_order_acquire);
        if(atomic_load_explicit(&quitting,memory_order_relaxed))return;
        if(current==seen){signal_wait(10);continue;}
        seen=current;think(w,&position);
        if(atomic_fetch_sub_explicit(&pending,1,memory_order_acq_rel)==1){
            result();atomic_store_explicit(&completed,seen,memory_order_release);notify(process_id,12);
        }
    }
}
/* Completion is distinct from the last search decrement: a new command must
 * not change workers/position while final bestmove publication is in flight. */
static void wait(void){
    atomic_store_explicit(&stopped,1,memory_order_relaxed);
    int target=atomic_load_explicit(&epoch,memory_order_relaxed);
    while(atomic_load_explicit(&completed,memory_order_acquire)!=target)signal_wait(12);
}
static void clear(void){for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=table[i].data=0;atomic_flag_clear(&table[i].lock);}}
static void set_position(char *s){
    Board b,c;uint64_t keys[HISTORY];int n=1;char *moves=strstr(s," moves "),*save;
    if(moves){*moves=0;moves+=7;}
    if(!strcmp(s,"startpos"))start(&b);
#if DEV
    else if(!strncmp(s,"fen ",4)){if(!fen(&b,s+4))return;}
#endif
    else return;
    keys[0]=b.h;
    if(moves)for(char *t=strtok_r(moves," \t",&save);t;t=strtok_r(0," \t",&save)){
        Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
static uint64_t number(const char *s){
    uint64_t n=0;if(!s||!*s)return 0;
    for(;*s;s++){unsigned d=(unsigned)(*s-'0');if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;n=n*10+d;}return n;
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
    wait();deadline=UINT64_MAX;
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
    for(char *t=strtok_r(s," \t",&save);t;t=strtok_r(0," \t",&save)){
        if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(0," \t",&save));if(side==position.s){clock=n;present=1;}}
        else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(0," \t",&save));if(side==position.s)inc=n;}
        else if(!strcmp(t,"infinite"))infinite=1;
#if DEV
        else if(!strcmp(t,"depth")){uint64_t n=number(strtok_r(0," \t",&save));if(n&&n<PLY-1)max_depth=(int)n;}
        else if(!strcmp(t,"nodes"))limit=number(strtok_r(0," \t",&save));
        else if(!strcmp(t,"movetime")){budget=number(strtok_r(0," \t",&save));if(!budget)budget=1;}
#endif
    }
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
    fallback=first(&position);atomic_store_explicit(&stopped,0,memory_order_relaxed);
    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}
    atomic_store_explicit(&pending,WORKERS,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake_workers(WORKERS);
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
    signals_init();
    table=allocate(((size_t)1<<TT_BITS)*sizeof *table);if(!table)return 2;clear();start(&position);game_keys[0]=position.h;game_length=1;
    for(;created<WORKERS;created++){
        workers[created].id=created;
        /* One inaccessible guard page precedes each private 1 MiB stack. */
        char *stack=allocate(1048576+4096);if(!stack){status=2;break;}
        if(CALL(10,stack,4096,0,0,0,0)||spawn(work,workers+created,stack+1048576+4096,(int *)(ids+created))<0){status=2;break;}
    }
    if(status)goto shutdown;
    while(atomic_load_explicit(&ready,memory_order_acquire)<WORKERS)signal_wait(12);
    for(;;){
        int valid=read_line(line);if(valid<0)break;if(!valid)continue;
        size_t n=strlen(line);while(n&&(line[n-1]=='\r'||line[n-1]==' '||line[n-1]=='\t'))line[--n]=0;
        if(!strcmp(line,"uci"))output("id name Rove4k D syscall\nuciok\n");
        else if(!strcmp(line,"isready"))output("readyok\n");
        else if(!strcmp(line,"quit"))break;
        else if(!strcmp(line,"stop"))wait();
        else if(!strcmp(line,"ucinewgame")){wait();clear();}
        else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}
        else if(!strcmp(line,"go")||!strncmp(line,"go ",3))go(line+2);
#if DEV
        else if(!strncmp(line,"perft ",6)){wait();uint64_t d=number(line+6);if(d<=8){char reply[80],*s=append(reply,"perft ");s=decimal(s,d);*s++=' ';s=decimal(s,perft(&position,(int)d));append(s,"\n");output(reply);}}
        else if(!strcmp(line,"legal")){wait();Move list[MOVES];Board b;int count=gen(&position,list);char reply[MOVES*7+8],*s=append(reply,"legal");for(int i=0;i<count;i++)if(make(&position,list[i],&b)){char name[6];text(list[i],name);*s++=' ';s=append(s,name);}append(s,"\n");output(reply);}
        else if(!strcmp(line,"eval")){wait();char reply[64],*s=append(reply,"eval ");s=signed_decimal(s,position.v*position.s);append(s,"\n");output(reply);}
        else if(!strcmp(line,"state")){wait();char reply[256],*s=append(reply,"{\"hash\":\"");for(int shift=60;shift>=0;shift-=4)*s++="0123456789abcdef"[(position.h>>shift)&15];s=append(s,"\",\"halfmove\":");s=decimal(s,position.half);s=append(s,",\"eval\":");s=signed_decimal(s,position.v*position.s);s=append(s,",\"draw\":");s=append(s,drawn()?"true":"false");s=append(s,",\"invariant\":");s=append(s,verify_board(&position)?"true":"false");append(s,"}\n");output(reply);}
        else if(!strcmp(line,"verify")){wait();Move list[MOVES];Board b;int good=verify_board(&position),count=gen(&position,list),tested=1;for(int i=0;i<count;i++)if(make(&position,list[i],&b)){good&=verify_board(&b);tested++;}char reply[80],*s=append(reply,good?"verify pass positions ":"verify fail positions ");s=decimal(s,tested);append(s,"\n");output(reply);}
        else if(!strcmp(line,"stats")){wait();stats();}
#endif
    }
    wait();
shutdown:
    atomic_store_explicit(&quitting,1,memory_order_relaxed);atomic_fetch_add_explicit(&epoch,1,memory_order_release);wake_workers(created);
    for(int i=0;i<created;i++){int id;while((id=atomic_load_explicit(ids+i,memory_order_acquire)))join_wait(ids+i,id);}
    return status;
}
