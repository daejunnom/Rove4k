/* Narrow actual-F DEV=0 query/child/transaction contract. Never submitted.
 * FEN is a fixture-only renamed copy of old F's DEV loader. Shipping ingress
 * remains startpos only; no production parser, board or MTD body is replaced. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <ctype.h>
#include <errno.h>
#define main engine_main
#include ENGINE_SOURCE
#undef main
#include "fixture-fen.h"

static int qc_value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),advance=v>0?q/16:7-q/16;
    int center=7-abs(2*(q%16)-7)-abs(2*(q/16)-7),n=material[a];
    if(a==1)n+=advance*7+center*2;
    if(a==2)n+=center*9;
    if(a==3)n+=center*5;
    if(a==4)n+=advance*2;
    if(a==5)n+=center*2;
    if(a==6)n-=center*3;
    return v>0?n:-n;
}
static int qc_scalar(const Board *b){int n=0;for(int q=0;q<128;q++)if(!(q&0x88))n+=qc_value(b->b[q],q);return n;}
static int qc_equal(const Board *a,const Board *b){
    return !memcmp(a->b,b->b,128)&&a->s==b->s&&a->c==b->c&&a->e==b->e&&
        a->k[0]==b->k[0]&&a->k[1]==b->k[1]&&a->half==b->half&&a->v==b->v&&a->h==b->h&&a->r==b->r;
}
static void qc_board(const Board *b){
    int scalar=qc_scalar(b);assert(b->v==scalar);
    printf("{\"b\":[");for(int i=0;i<128;i++)printf("%s%d",i?",":"",b->b[i]);
    printf("],\"s\":%d,\"c\":%d,\"e\":%d,\"k\":[%d,%d],\"half\":%d,\"h\":\"%016llx\",\"r\":\"%016llx\",\"v\":%d,\"scalar\":%d}",
        b->s,b->c,b->e,b->k[0],b->k[1],b->half,(unsigned long long)b->h,(unsigned long long)b->r,b->v,scalar);
}
static Move qc_reference(const Board *b,const char *token,Board *child){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){if(token){text(list[i],name);if(strcmp(name,token))continue;}if(make(b,list[i],child))return list[i];}return 0;
}
static Move qc_query(const Board *b,const char *token,Board *child){
#if CANDIDATE
    return parse(b,token,child);
#else
    Move m=token?parse(b,token):first(b);if(m)assert(make(b,m,child));return m;
#endif
}
static const char *qc_names[]={"start","castle-white","castle-black","ep-white","ep-black","pinned-ep","promotion-white","promotion-black","mate","stalemate","pinned-rook","king-target"};
static const char *qc_fens[]={
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "6k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "4k3/8/8/8/3Pp3/8/8/6K1 b - d3 0 1",
    "4r1k1/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "r1r4k/1P6/8/8/8/8/8/7K w - - 0 1",
    "7k/8/8/8/8/8/1p6/R1R4K b - - 0 1",
    "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
    "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
    "4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1",
    "k7/8/8/8/8/8/8/R6K w - - 0 1"
};
static const char *qc_invalid[]={""," ","e2e4 "," e2e4","E2E4","e2E4","e2e4q","a0a1","a1a9","i1a1","a1i1","a1a1","e2e5x","e2e4junk","b7b8","b7b8k","b7b8p","b7b8Q","b7b8qq","e5d6q","b2b1","b2b1k","b2b1Q","\te2e4"};
static void qc_queries(void){
    atomic_store(&stopped,1);printf("\"queries\":[");
    for(unsigned c=0;c<sizeof qc_names/sizeof *qc_names;c++){
        Board b,before,scratch,wanted;assert(fixture_fen_board(&b,qc_fens[c]));before=b;
        Move expected=qc_reference(&b,0,&wanted),got=qc_query(&b,0,&scratch);
        assert(got==expected&&qc_equal(&b,&before));if(got)assert(qc_equal(&scratch,&wanted));
        printf("%s{\"name\":\"%s\",\"fen\":\"%s\",\"board\":",c?",":"",qc_names[c],qc_fens[c]);qc_board(&b);
        printf(",\"first\":%u,\"first_child\":",got);if(got)qc_board(&scratch);else printf("null");printf(",\"legal_queries\":[");
        Move list[MOVES];int n=gen(&b,list),legal=0,illegal=0,promotions=0;assert(n>=0&&n<=MOVES);
        for(int i=0;i<n;i++){
            Board child;char token[6];text(list[i],token);
            if(!make(&b,list[i],&child)){assert(!qc_query(&b,token,&scratch)&&qc_equal(&b,&before));illegal++;continue;}
            Move found=qc_query(&b,token,&scratch);
            assert(found==list[i]&&qc_equal(&scratch,&child)&&qc_equal(&b,&before));
            assert(qc_reference(&b,token,&wanted)==found&&qc_equal(&scratch,&wanted));
            printf("%s{\"token\":\"%s\",\"move\":%u,\"child\":",legal++?",":"",token,found);qc_board(&scratch);putchar('}');
            promotions+=PROMO(found)!=0;
        }
        if(c==6||c==7)assert(promotions==12);
        if(c==8||c==9)assert(!legal&&!got);
        if(c==10||c==11)assert(illegal>0);
        for(unsigned i=0;i<sizeof qc_invalid/sizeof *qc_invalid;i++){
            assert(!qc_reference(&b,qc_invalid[i],&wanted));assert(!qc_query(&b,qc_invalid[i],&scratch)&&qc_equal(&b,&before));
        }
        printf("],\"invalid_rejected\":24,\"generated_illegal_rejected\":%d,\"promotions\":%d}",illegal,promotions);
    }
    assert(atomic_load(&stopped)==1);printf("],\"query_stopped_unchanged\":true,");
}
static uint64_t qc_digest(const uint64_t *keys,int n){uint64_t h=UINT64_C(1469598103934665603);for(int i=0;i<n;i++)h=(h^keys[i])*UINT64_C(1099511628211);return h;}
static void qc_seed(void){assert(fixture_fen_board(&position,"7k/8/8/8/8/8/8/KR6 w - - 0 1"));game_length=2;for(int i=0;i<HISTORY;i++)game_keys[i]=mix((unsigned)i+17);game_keys[0]=position.h;}
static int qc_transaction_count;
static void qc_transaction(const char *name,const char *command,int accepted,const Board *expected,const uint64_t *keys,int length){
    qc_seed();Board before=position;uint64_t previous[HISTORY];memcpy(previous,game_keys,sizeof previous);
    char *line=malloc(strlen(command)+1);assert(line);strcpy(line,command);set_position(line);free(line);
    if(accepted){assert(qc_equal(&position,expected)&&game_length==length);for(int i=0;i<HISTORY;i++)assert(game_keys[i]==(i<length?keys[i]:previous[i]));}
    else {assert(qc_equal(&position,&before)&&game_length==2);for(int i=0;i<HISTORY;i++)assert(game_keys[i]==previous[i]);}
    printf("%s{\"name\":\"%s\",\"accepted\":%s,\"length\":%d,\"board\":",qc_transaction_count++?",":"",name,accepted?"true":"false",game_length);
    qc_board(&position);printf(",\"keys_digest\":\"%016llx\"}",(unsigned long long)qc_digest(game_keys,HISTORY));
}
static void qc_expected(Board *b,uint64_t *keys,int *n,const char *token){Board child;assert(qc_reference(b,token,&child));*b=child;keys[(*n)++]=b->h;}
static void qc_transactions(void){
    Board b;uint64_t keys[HISTORY];int n=1;start(&b);keys[0]=b.h;
    qc_expected(&b,keys,&n,"e2e4");qc_expected(&b,keys,&n,"e7e5");qc_expected(&b,keys,&n,"g1f3");qc_expected(&b,keys,&n,"b8c6");
    printf("\"transactions\":[");
    qc_transaction("valid-replay","startpos moves e2e4 e7e5 g1f3 b8c6",1,&b,keys,n);
    qc_transaction("invalid-middle","startpos moves e2e4 e7e5 b1b9 b8c6",0,0,0,0);
    qc_transaction("invalid-after-prefix","startpos moves e2e4 e7e5 g1f3 nonsense",0,0,0,0);
    qc_transaction("shipping-fen-rejected","fen 7k/8/8/8/8/8/8/KR6 w - - 0 1 moves b1b2",0,0,0,0);
    start(&b);n=1;keys[0]=b.h;qc_transaction("empty-move-list","startpos moves ",1,&b,keys,n);
    const char *cycle[]={"g1f3","g8f6","f3g1","f6g8"};
    char *command=malloc(14+HISTORY*5+1);assert(command);strcpy(command,"startpos moves");size_t used=strlen(command);
    for(int i=0;i<HISTORY-1;i++){used+=(size_t)sprintf(command+used," %s",cycle[i&3]);qc_expected(&b,keys,&n,cycle[i&3]);}
    assert(n==HISTORY);qc_transaction("history-boundary-4095",command,1,&b,keys,n);
    sprintf(command+used," %s",cycle[(HISTORY-1)&3]);qc_transaction("history-overflow-4096",command,0,0,0,0);free(command);printf("],");
}
static void qc_think(int production){
    Worker *w=calloc(1,sizeof *w),*before=malloc(sizeof *before);assert(w&&before);Board b;start(&b);
    w->id=7;w->depth=33;w->score=999;w->nodes=123456;w->best=MOVE(20,52,0);Move seed=w->best;
    for(int i=0;i<128;i++)for(int j=0;j<128;j++)w->history[i][j]=(int16_t)((i*7+j)%31-15);
    for(int i=0;i<13;i++)for(int j=0;j<13;j++)w->continuation[i][j]=(int16_t)(i*3-j);
    for(int i=0;i<1024;i++)w->correction[i]=(int16_t)(i%23-11);
    for(int i=0;i<HISTORY+PLY;i++)w->keys[i]=mix((unsigned)i+99);
    *before=*w;game_length=3;for(int i=0;i<game_length;i++)game_keys[i]=mix((unsigned)i+1000);
    atomic_store(&stopped,1);deadline=UINT64_MAX;
#if !CANDIDATE
    if(production){w->depth=w->score=0;w->best=0;w->nodes=0;}
#endif
    think(w,&b);
    assert(!w->nodes&&!w->depth&&!w->score&&w->id==before->id&&w->length==game_length&&atomic_load(&stopped)==1);
    assert(w->best==(production||CANDIDATE?0:seed));
    assert(!memcmp(w->history,before->history,sizeof w->history)&&!memcmp(w->continuation,before->continuation,sizeof w->continuation)&&!memcmp(w->correction,before->correction,sizeof w->correction));
    for(int i=0;i<HISTORY+PLY;i++)assert(w->keys[i]==(i<game_length?game_keys[i]:before->keys[i]));
    printf("{\"best\":%u,\"seed_best\":%u,\"nodes\":%llu,\"depth\":%d,\"score\":%d,\"id\":%d,\"length\":%d,\"heuristics_preserved\":true,\"keys_loaded\":true,\"tail_keys_preserved\":true,\"stopped_preserved\":true",
        w->best,seed,(unsigned long long)w->nodes,w->depth,w->score,w->id,w->length);
    if(production){Board child;Move fallback_move=qc_query(&b,0,&child);assert(fallback_move);printf(",\"resolved_fallback\":%u",w->best?w->best:fallback_move);}
    putchar('}');free(before);free(w);
}
int main(void){
    assert(sizeof(Board)==176&&MOVES==512&&HISTORY==4096&&PLY==128&&DEV==0&&WORKERS==2&&TT_BITS==18);
    for(int v=-6;v<=6;v++)for(int sq=0;sq<64;sq++){int q=(sq/8)*16+sq%8,expected=qc_value(v,q);assert(value(v,q)==expected);}
    printf("{\"passed\":true,\"board_bytes\":176,\"piece_square_terms\":832,\"shared\":{");qc_queries();qc_transactions();
    printf("\"production_think\":");qc_think(1);printf("},\"direct_think\":");qc_think(0);puts("}");return 0;
}
