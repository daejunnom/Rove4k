/* Narrow private-query/worker-entry contract fixture, never submitted. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#define main engine_main
#include ENGINE_SOURCE
#undef main

static int qc_equal(const Board *a,const Board *b){
    for(int i=0;i<128;i++)if(a->b[i]!=b->b[i])return 0;
    return a->s==b->s&&a->c==b->c&&a->e==b->e&&a->k[0]==b->k[0]&&a->k[1]==b->k[1]&&
        a->half==b->half&&a->v==b->v&&a->h==b->h&&a->r==b->r;
}
static void qc_board(const Board *b){
    assert(verify_board(b));printf("{\"b\":[");
    for(int i=0;i<128;i++)printf("%s%d",i?",":"",b->b[i]);
    printf("],\"s\":%d,\"c\":%d,\"e\":%d,\"k\":[%d,%d],\"half\":%d,\"v\":%d,\"h\":\"%016llx\",\"r\":\"%016llx\"}",
        b->s,b->c,b->e,b->k[0],b->k[1],b->half,b->v,(unsigned long long)b->h,(unsigned long long)b->r);
}
static Move qc_reference(const Board *b,const char *token,Board *child){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){
        if(token){text(list[i],name);if(strcmp(name,token))continue;}
        if(make(b,list[i],child))return list[i];
    }return 0;
}
static Move qc_query(const Board *b,const char *token,Board *child){
#if CANDIDATE
    return parse(b,token,child);
#else
    Move m=token?parse(b,token):first(b);
    if(m)assert(make(b,m,child));
    return m;
#endif
}
static const char *qc_names[]={"start","castle-white","castle-black","ep-white","ep-black","pinned-ep","promotion-white","promotion-black"};
static const char *qc_fens[]={
    0,
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "4k3/8/8/8/3Pp3/8/8/6K1 b - d3 0 1",
    "4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "r1r4k/1P6/8/8/8/8/8/7K w - - 0 1",
    "7k/8/8/8/8/8/1p6/R1R4K b - - 0 1"
};
static const char *qc_invalid[]={""," ","e2e4 "," e2e4","E2E4","e2E4","e2e4q","a0a1","a1a9","i1a1","a1i1","a1a1","e2e5","e2e4junk","b7b8","b7b8k","b7b8p","b7b8Q","b7b8qq","e5d6q","b2b1","b2b1k","b2b1Q","\te2e4"};
static void qc_queries(void){
    atomic_store(&stopped,1);
    printf("\"queries\":[");
    for(int c=0;c<8;c++){
        Board b,before,scratch,wanted;if(qc_fens[c])assert(fen(&b,qc_fens[c]));else start(&b);before=b;
        Move expected=qc_reference(&b,0,&wanted),first_move=qc_query(&b,0,&scratch);
        assert(first_move==expected&&expected&&qc_equal(&scratch,&wanted)&&qc_equal(&b,&before));
        printf("%s{\"name\":\"%s\",\"board\":",c?",":"",qc_names[c]);qc_board(&b);
        printf(",\"first\":%u,\"first_child\":",first_move);qc_board(&scratch);printf(",\"legal_queries\":[");
        Move list[MOVES];int n=gen(&b,list),legal=0,promotions=0;
        for(int i=0;i<n;i++){
            Board child;if(!make(&b,list[i],&child))continue;char token[6];text(list[i],token);
            Move found=qc_query(&b,token,&scratch);
            assert(found==list[i]&&qc_equal(&scratch,&child)&&qc_equal(&b,&before));
            assert(qc_reference(&b,token,&wanted)==found&&qc_equal(&scratch,&wanted));
            printf("%s{\"token\":\"%s\",\"move\":%u,\"child\":",legal++?",":"",token,found);qc_board(&scratch);putchar('}');
            promotions+=PROMO(found)!=0;
        }
        if(c>=6)assert(promotions==12);
        for(unsigned i=0;i<sizeof qc_invalid/sizeof *qc_invalid;i++){
            assert(!qc_reference(&b,qc_invalid[i],&wanted));
            assert(!qc_query(&b,qc_invalid[i],&scratch));assert(qc_equal(&b,&before));
            /* scratch is deliberately not inspected after failed query. */
        }
        printf("],\"invalid_rejected\":%u}",(unsigned)(sizeof qc_invalid/sizeof *qc_invalid));
    }puts("],");
    Board terminal,before,scratch;assert(fen(&terminal,"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"));before=terminal;
    assert(!qc_query(&terminal,0,&scratch)&&qc_equal(&terminal,&before));
    assert(atomic_load(&stopped)==1);printf("\"terminal_first\":0,\"query_stopped_unchanged\":true,");
}
static uint64_t qc_digest(const uint64_t *keys,int n){
    uint64_t h=UINT64_C(1469598103934665603);for(int i=0;i<n;i++)h=(h^keys[i])*UINT64_C(1099511628211);return h;
}
static void qc_seed(void){
    assert(fen(&position,"7k/8/8/8/8/8/8/KR6 w - - 0 1"));
    game_length=2;for(int i=0;i<HISTORY;i++)game_keys[i]=mix((unsigned)i+17);game_keys[0]=position.h;
}
static int qc_transaction_count;
static void qc_transaction(const char *name,const char *command,int accepted,const Board *expected,const uint64_t *keys,int length){
    qc_seed();Board before=position;uint64_t previous[HISTORY];memcpy(previous,game_keys,sizeof previous);
    char *line=malloc(strlen(command)+1);assert(line);strcpy(line,command);set_position(line);free(line);
    if(accepted){
        assert(qc_equal(&position,expected)&&game_length==length);
        for(int i=0;i<HISTORY;i++)assert(game_keys[i]==(i<length?keys[i]:previous[i]));
    }else{
        assert(qc_equal(&position,&before)&&game_length==2);
        for(int i=0;i<HISTORY;i++)assert(game_keys[i]==previous[i]);
    }
    printf("%s{\"name\":\"%s\",\"accepted\":%s,\"length\":%d,\"board\":",qc_transaction_count++?",":"",name,accepted?"true":"false",game_length);
    qc_board(&position);printf(",\"keys_digest\":\"%016llx\"}",(unsigned long long)qc_digest(game_keys,HISTORY));
}
static void qc_expected(Board *b,uint64_t *keys,int *n,const char *token){
    Board child;assert(qc_reference(b,token,&child));*b=child;keys[(*n)++]=b->h;
}
static void qc_transactions(void){
    Board b;uint64_t keys[HISTORY];int n=1;start(&b);keys[0]=b.h;
    qc_expected(&b,keys,&n,"e2e4");qc_expected(&b,keys,&n,"e7e5");qc_expected(&b,keys,&n,"g1f3");qc_expected(&b,keys,&n,"b8c6");
    printf("\"transactions\":[");
    qc_transaction("valid-replay","startpos moves e2e4 e7e5 g1f3 b8c6",1,&b,keys,n);
    qc_transaction("invalid-middle","startpos moves e2e4 e7e5 b1b9 b8c6",0,0,0,0);
    qc_transaction("invalid-after-prefix","startpos moves e2e4 e7e5 g1f3 nonsense",0,0,0,0);
    qc_transaction("matched-pinned-move","fen 4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1 moves e2f2",0,0,0,0);
    qc_transaction("malformed-fen","fen 8/8/8/8/8/8/8/K7 w - - 0 1 moves a1b1",0,0,0,0);
    start(&b);n=1;keys[0]=b.h;qc_transaction("empty-move-list","startpos moves ",1,&b,keys,n);
    for(int kind=2;kind<=5;kind++){
        assert(fen(&b,qc_fens[6]));n=1;keys[0]=b.h;char token[6]="b7b8n",command[160],name[40];token[4]="  nbrq"[kind];
        qc_expected(&b,keys,&n,token);snprintf(command,sizeof command,"fen %s moves %s",qc_fens[6],token);
        snprintf(name,sizeof name,"promotion-%c",token[4]);qc_transaction(name,command,1,&b,keys,n);
    }
    assert(fen(&b,qc_fens[3]));n=1;keys[0]=b.h;qc_expected(&b,keys,&n,"e5d6");
    qc_transaction("ep-replay","fen 6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1 moves e5d6",1,&b,keys,n);
    assert(fen(&b,qc_fens[1]));n=1;keys[0]=b.h;qc_expected(&b,keys,&n,"e1g1");qc_expected(&b,keys,&n,"e8c8");
    qc_transaction("castle-replay","fen r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1 moves e1g1 e8c8",1,&b,keys,n);
    const char *cycle[]={"g1f3","g8f6","f3g1","f6g8"};
    char *long_command=malloc(14+HISTORY*5+1);assert(long_command);strcpy(long_command,"startpos moves");size_t used=strlen(long_command);
    start(&b);n=1;keys[0]=b.h;
    for(int i=0;i<HISTORY-1;i++){
        used+=(size_t)sprintf(long_command+used," %s",cycle[i&3]);qc_expected(&b,keys,&n,cycle[i&3]);
    }
    assert(n==HISTORY);qc_transaction("history-boundary-4095",long_command,1,&b,keys,n);
    sprintf(long_command+used," %s",cycle[(HISTORY-1)&3]);qc_transaction("history-overflow-4096",long_command,0,0,0,0);free(long_command);
    printf("],");
}
static void qc_think_case(const char *name,int prestopped,int production){
    Worker *w=calloc(1,sizeof *w),*before=malloc(sizeof *before);assert(w&&before);Board b;start(&b);
    w->id=7;w->depth=33;w->score=999;w->nodes=123456;w->best=MOVE(20,52,0);Move seed=w->best;
    for(int i=0;i<128;i++)for(int j=0;j<128;j++)w->history[i][j]=(int16_t)((i*7+j)%31-15);
    for(int i=0;i<13;i++)for(int j=0;j<13;j++)w->continuation[i][j]=(int16_t)(i*3-j);
    for(int i=0;i<1024;i++)w->correction[i]=(int16_t)(i%23-11);
    for(int i=0;i<HISTORY+PLY;i++)w->keys[i]=mix((unsigned)i+99);
    w->pvs=11;w->qs=12;w->hits=13;w->hist_updates=14;w->cont_updates=15;w->corr_updates=16;w->corr_uses=17;w->ply_aborts=18;
    *before=*w;game_length=3;for(int i=0;i<game_length;i++)game_keys[i]=mix((unsigned)i+1000);
    atomic_store(&stopped,prestopped);max_depth=prestopped?4:0;deadline=UINT64_MAX;
#if !CANDIDATE
    if(production){w->depth=w->score=0;w->best=0;w->nodes=0;}
#endif
    think(w,&b);
    assert(!w->nodes&&!w->depth&&!w->score&&w->id==before->id&&w->length==game_length&&atomic_load(&stopped)==prestopped);
    assert(w->best==(production||CANDIDATE?0:seed));
    assert(!memcmp(w->history,before->history,sizeof w->history)&&!memcmp(w->continuation,before->continuation,sizeof w->continuation)&&!memcmp(w->correction,before->correction,sizeof w->correction));
    for(int i=0;i<HISTORY+PLY;i++)assert(w->keys[i]==(i<game_length?game_keys[i]:before->keys[i]));
    assert(w->pvs==11&&w->qs==12&&w->hits==13&&w->hist_updates==14&&w->cont_updates==15&&w->corr_updates==16&&w->corr_uses==17&&w->ply_aborts==18);
    printf("{\"case\":\"%s\",\"best\":%u,\"nodes\":%llu,\"depth\":%d,\"score\":%d,\"id\":%d,\"length\":%d,\"heuristics_preserved\":true,\"keys_loaded\":true,\"tail_keys_preserved\":true,\"counters_preserved\":true,\"stopped_preserved\":true",
        name,w->best,(unsigned long long)w->nodes,w->depth,w->score,w->id,w->length);
    if(production){Board child;Move fallback_move=qc_query(&b,0,&child);assert(fallback_move);printf(",\"resolved_fallback\":%u",w->best?w->best:fallback_move);}
    else printf(",\"seed_best\":%u",seed);
    putchar('}');free(before);free(w);
}
int main(void){
    printf("{\"passed\":true,\"shared\":{");qc_queries();qc_transactions();
    printf("\"production_think\":[");qc_think_case("production-prestopped",1,1);putchar(',');qc_think_case("production-zero",0,1);
    printf("]},\"direct_think\":[");qc_think_case("seed-prestopped",1,0);putchar(',');qc_think_case("seed-zero",0,0);puts("]}");return 0;
}
