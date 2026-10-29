/* Shared readable protocol bodies, assembled before the existing shipping
 * transforms. Separate fragments retain different parse result and worker
 * startup contracts. This file does not add a runtime protocol abstraction. */

/* rove:begin now */
uint64_t now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
/* rove:end now */

/* rove:begin text */
static void text(Move m,char *s){
    if(!m){strcpy(s,"0000");return;}
    s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;
}
/* rove:end text */

/* rove:begin parse_with_board */
static Move parse(const Board *b,const char *s,Board *c){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){
        if(s){text(list[i],name);if(strcmp(s,name))continue;}
        if(make(b,list[i],c))return list[i];
    }return 0;
}
/* rove:end parse_with_board */

/* rove:begin parse_move_only */
static Move parse(const Board *b,const char *s){
    Move list[MOVES];Board c;char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;
}
/* rove:end parse_move_only */

/* rove:begin first_legal */
static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
/* rove:end first_legal */

/* rove:begin result */
static void result(void){
    flockfile(stdout);
    Worker *w=workers;for(int i=1;i<WORKERS;i++)if(workers[i].depth>w->depth)w=workers+i;
    Move best=w->best?w->best:fallback;char move[6];text(best,move);
#if DEV
    int score=w->score;
    if(abs(score)>=MATE-PLY)printf("info depth %d score mate %d",w->depth,score>0?(MATE-score+1)/2:-(MATE+score+1)/2);
    else printf("info depth %d score cp %d",w->depth,score);
    printf(" nodes %llu",(unsigned long long)atomic_load(&searched));if(best)printf(" pv %s",move);puts("");
#endif
    printf("bestmove %s\n",move);fflush(stdout);funlockfile(stdout);
}
/* rove:end result */

/* rove:begin work_pending_start */
static void *work(void *p){
    Worker *w=p;unsigned seen=0;pthread_mutex_lock(&mutex);--pending;pthread_cond_broadcast(&finished);
    for(;;){
        while(seen==epoch&&!quitting)pthread_cond_wait(&command,&mutex);
        if(quitting)break;
        seen=epoch;pthread_mutex_unlock(&mutex);think(w,&position);pthread_mutex_lock(&mutex);
        if(!--pending){result();pthread_cond_broadcast(&finished);}
    }
    pthread_mutex_unlock(&mutex);return NULL;
}
/* rove:end work_pending_start */

/* rove:begin work_ready_start */
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
/* rove:end work_ready_start */

/* rove:begin wait */
static void wait(void){atomic_store(&stopped,1);pthread_mutex_lock(&mutex);while(pending)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);}
/* rove:end wait */

/* rove:begin clear */
static void clear(void){for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=table[i].data=0;atomic_flag_clear(&table[i].lock);}}
/* rove:end clear */

/* rove:begin set_position_with_board */
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
        if(n==HISTORY||!parse(&b,t,&c))return;b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
/* rove:end set_position_with_board */

/* rove:begin set_position_remake */
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
/* rove:end set_position_remake */

/* rove:begin number */
static uint64_t number(const char *s){
    uint64_t n=0;if(!s||!*s)return 0;
    for(;*s;s++){unsigned d=(unsigned)(*s-'0');if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;n=n*10+d;}return n;
}
/* rove:end number */

/* rove:begin read_line */
static int read_line(char *s){
    int c,n=0,bad=0;
    while((c=getchar())!=EOF&&c!='\n'){if(!c||n==32767)bad=1;else s[n++]=c;}
    s[n]=0;return c==EOF&&!n?-1:!bad;
}
/* rove:end read_line */

/* rove:begin go_with_board */
static void go(char *s){
    wait();
#if DEV
    deadline=UINT64_MAX;
#endif
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
#if DEV
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
#else
    uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
#endif
    for(char *t=strtok_r(s," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s){clock=n;present=1;}}
        else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s)inc=n;}
#if DEV
        else if(!strcmp(t,"infinite"))infinite=1;
        else if(!strcmp(t,"depth")){uint64_t n=number(strtok_r(NULL," \t",&save));if(n&&n<PLY-1)max_depth=n;}
        else if(!strcmp(t,"nodes"))limit=number(strtok_r(NULL," \t",&save));
        else if(!strcmp(t,"movetime")){budget=number(strtok_r(NULL," \t",&save));if(!budget)budget=1;}
#endif
    }
#if DEV
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
#else
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
#endif
    Board c;fallback=parse(&position,0,&c);atomic_store(&stopped,0);
    pthread_mutex_lock(&mutex);pending=WORKERS;epoch++;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
}
/* rove:end go_with_board */

/* rove:begin go_move_only */
static void go(char *s){
    wait();
#if DEV
    deadline=UINT64_MAX;
#endif
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
#if DEV
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
#else
    uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
#endif
    for(char *t=strtok_r(s," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        if(!strcmp(t,"wtime")||!strcmp(t,"btime")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s){clock=n;present=1;}}
        else if(!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s)inc=n;}
#if DEV
        else if(!strcmp(t,"infinite"))infinite=1;
        else if(!strcmp(t,"depth")){uint64_t n=number(strtok_r(NULL," \t",&save));if(n&&n<PLY-1)max_depth=n;}
        else if(!strcmp(t,"nodes"))limit=number(strtok_r(NULL," \t",&save));
        else if(!strcmp(t,"movetime")){budget=number(strtok_r(NULL," \t",&save));if(!budget)budget=1;}
#endif
    }
#if DEV
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
#else
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
#endif
    fallback=first(&position);atomic_store(&stopped,0);
    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}
    pthread_mutex_lock(&mutex);pending=WORKERS;epoch++;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
}
/* rove:end go_move_only */
