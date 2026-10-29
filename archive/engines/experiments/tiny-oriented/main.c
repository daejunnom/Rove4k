#include "tiny.h"

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

static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t command=PTHREAD_COND_INITIALIZER,finished=PTHREAD_COND_INITIALIZER;
static unsigned epoch;
static int pending,ready,quitting;
static Move fallback;

uint64_t now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static void text(const Board *b,Move m,char *s){
    if(!m){strcpy(s,"0000");return;}
    int flip=b->s<0?112:0,from=FROM(m)^flip,to=TO(m)^flip;
    s[0]='a'+(from&7);s[1]='1'+(from>>4);s[2]='a'+(to&7);s[3]='1'+(to>>4);
    s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;
}
static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
static Move parse(const Board *b,const char *s){
    Move list[MOVES];Board c;char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(b,list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;
}
static void result(void){
    flockfile(stdout);
    Worker *w=workers;for(int i=1;i<WORKERS;i++)if(workers[i].depth>w->depth)w=workers+i;
    Move best=w->best?w->best:fallback;char move[6];text(&position,best,move);
#if DEV
    int score=w->score;
    if(abs(score)>=MATE-PLY)printf("info depth %d score mate %d",w->depth,score>0?(MATE-score+1)/2:-(MATE+score+1)/2);
    else printf("info depth %d score cp %d",w->depth,score);
    printf(" nodes %llu",(unsigned long long)atomic_load(&searched));if(best)printf(" pv %s",move);puts("");
#endif
    printf("bestmove %s\n",move);fflush(stdout);funlockfile(stdout);
}
static void *work(void *p){
    Worker *w=p;unsigned seen=0;pthread_mutex_lock(&mutex);ready++;pthread_cond_broadcast(&finished);
    for(;;){
        while(seen==epoch&&!quitting)pthread_cond_wait(&command,&mutex);
        if(quitting)break;
        seen=epoch;pthread_mutex_unlock(&mutex);think(w,&position);pthread_mutex_lock(&mutex);
        if(!--pending){result();pthread_cond_broadcast(&finished);}
    }
    pthread_mutex_unlock(&mutex);return NULL;
}
static void wait(void){atomic_store(&stopped,1);pthread_mutex_lock(&mutex);while(pending)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);}
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
    if(moves)for(char *t=strtok_r(moves," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
static uint64_t number(const char *s){
    uint64_t n=0;if(!s||!*s)return 0;
    for(;*s;s++){unsigned d=(unsigned)(*s-'0');if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;n=n*10+d;}return n;
}
static int read_line(char *s){
    int c,n=0,bad=0;
    while((c=getchar())!=EOF&&c!='\n'){if(!c||n==32767)bad=1;else s[n++]=c;}
    s[n]=0;return c==EOF&&!n?-1:!bad;
}
static void go(char *s){
    wait();deadline=UINT64_MAX;
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
    for(char *t=strtok_r(s," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s){clock=n;present=1;}}
        else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s)inc=n;}
        else if(!strcmp(t,"infinite"))infinite=1;
#if DEV
        else if(!strcmp(t,"depth")){uint64_t n=number(strtok_r(NULL," \t",&save));if(n&&n<PLY-1)max_depth=n;}
        else if(!strcmp(t,"nodes"))limit=number(strtok_r(NULL," \t",&save));
        else if(!strcmp(t,"movetime")){budget=number(strtok_r(NULL," \t",&save));if(!budget)budget=1;}
#endif
    }
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
    fallback=first(&position);atomic_store(&stopped,0);
    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}
    pthread_mutex_lock(&mutex);pending=WORKERS;epoch++;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
}
#if DEV
static uint64_t perft(const Board *b,int d){
    if(!d)return 1;
    uint64_t total=0;Move list[MOVES];Board c;int n=gen(b,list);
    for(int i=0;i<n;i++)if(make(b,list[i],&c))total+=perft(&c,d-1);
    return total;
}
static int drawn(void){int n=0;for(int i=0;i<game_length;i++)n+=game_keys[i]==position.h;return position.half>=100||n>=3||dead(&position);}
static void stats(void){
    uint64_t pvs=0,qs=0,hits=0,hist=0,cont=0,corr=0,uses=0,aborts=0;int depth=0;
    for(int i=0;i<WORKERS;i++){
        Worker *w=workers+i;if(w->depth>depth)depth=w->depth;
        pvs+=w->pvs;qs+=w->qs;hits+=w->hits;hist+=w->hist_updates;cont+=w->cont_updates;corr+=w->corr_updates;uses+=w->corr_uses;aborts+=w->ply_aborts;
    }
    printf("{\"workers\":%d,\"total_threads\":%d,\"nodes\":%llu,\"completed_depth\":%d,\"pvs\":%llu,\"qs\":%llu,\"tt_hits\":%llu,\"history_updates\":%llu,\"continuation_updates\":%llu,\"correction_updates\":%llu,\"correction_uses\":%llu,\"ply_aborts\":%llu}\n",WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched),depth,(unsigned long long)pvs,(unsigned long long)qs,(unsigned long long)hits,(unsigned long long)hist,(unsigned long long)cont,(unsigned long long)corr,(unsigned long long)uses,(unsigned long long)aborts);fflush(stdout);
}
#endif
int main(void){
    pthread_t threads[WORKERS];int created=0,status=0;char line[32768];
    table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;clear();start(&position);game_keys[0]=position.h;game_length=1;
    for(;created<WORKERS;created++){workers[created].id=created;if(pthread_create(threads+created,NULL,work,workers+created)){status=2;goto shutdown;}}
    pthread_mutex_lock(&mutex);while(ready<WORKERS)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);
    for(;;){
        int status=read_line(line);if(status<0)break;if(!status)continue;
        size_t n=strlen(line);
        while(n&&(line[n-1]=='\n'||line[n-1]=='\r'||line[n-1]==' '||line[n-1]=='\t'))line[--n]=0;
        if(!strcmp(line,"uci")){puts("id name Rove4k A\nuciok");fflush(stdout);}
        else if(!strcmp(line,"isready")){puts("readyok");fflush(stdout);}
        else if(!strcmp(line,"quit"))break;
        else if(!strcmp(line,"stop"))wait();
        else if(!strcmp(line,"ucinewgame")){wait();clear();}
        else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}
        else if(!strcmp(line,"go")||!strncmp(line,"go ",3))go(line+2);
#if DEV
        else if(!strncmp(line,"perft ",6)){wait();uint64_t d=number(line+6);if(d<=8)printf("perft %d %llu\n",(int)d,(unsigned long long)perft(&position,d));fflush(stdout);}
        else if(!strcmp(line,"legal")){wait();Move list[MOVES];Board b;int count=gen(&position,list);printf("legal");for(int i=0;i<count;i++)if(make(&position,list[i],&b)){char s[6];text(&position,list[i],s);printf(" %s",s);}puts("");fflush(stdout);}
        else if(!strcmp(line,"eval")){wait();printf("eval %d\n",position.v);fflush(stdout);}
        else if(!strcmp(line,"state")){wait();printf("{\"hash\":\"%016llx\",\"halfmove\":%d,\"eval\":%d,\"draw\":%s,\"invariant\":%s}\n",(unsigned long long)position.h,position.half,position.v,drawn()?"true":"false",verify_board(&position)?"true":"false");fflush(stdout);}
        else if(!strcmp(line,"verify")){wait();Move list[MOVES];Board b;int good=verify_board(&position),count=gen(&position,list),tested=1;for(int i=0;i<count;i++)if(make(&position,list[i],&b)){good&=verify_board(&b);tested++;}printf("verify %s positions %d\n",good?"pass":"fail",tested);fflush(stdout);}
        else if(!strcmp(line,"stats")){wait();stats();}
#endif
    }
    wait();
shutdown:
    pthread_mutex_lock(&mutex);quitting=1;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
    for(int i=0;i<created;i++)if(pthread_join(threads[i],NULL))status=2;
    free(table);return status;
}
