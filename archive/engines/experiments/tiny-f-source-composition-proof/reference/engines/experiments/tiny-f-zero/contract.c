/* Actual frozen shipping source (already preprocessed/named) or readable DEV.
 * Only this private fixture adapts the old unit-window vs new beta-only API. */
#define main frozen_entry_main
#include ENGINE_SOURCE
#undef main
#include <assert.h>
#include <ctype.h>
#if FIXTURE_SHIPPING
#define T_START ae
#define T_MIX ag
#define T_PUT aF
#define T_STATE aD
#define T_EP aE
#define T_MAKE ab
#define T_GEN ah
#define T_PROBE ak
#define T_THINK ac
#define T_CLEAR az
#define T_QUIET_SCORE ap
#define T_SEARCH aj
#else
#define T_START start
#define T_MIX mix
#define T_PUT put
#define T_STATE state
#define T_EP ep
#define T_MAKE make
#define T_GEN gen
#define T_PROBE probe
#define T_THINK think
#define T_CLEAR clear
#define T_QUIET_SCORE quiet_score
#define T_SEARCH search
#endif
#if ZERO
#define query(w,p,d,b,ply,prior,move) T_SEARCH((w),(p),(d),(b),(ply),(prior),(move))
#else
#define query(w,p,d,b,ply,prior,move) T_SEARCH((w),(p),(d),(b)-1,(b),(ply),(prior),(move))
#endif
#include "cases.h"

static uint64_t digest=UINT64_C(1469598103934665603);
static void bytes(const void *data,size_t n){const unsigned char *p=data;while(n--)digest=(digest^*p++)*UINT64_C(1099511628211);}
static uint64_t state_digest(Worker *w){
    digest=UINT64_C(1469598103934665603);
    bytes(w->history,sizeof w->history);bytes(w->continuation,sizeof w->continuation);bytes(w->correction,sizeof w->correction);
    bytes(w->keys,w->length*sizeof *w->keys);bytes(&w->length,sizeof w->length);
    for(int i=0;i<(1<<TT_BITS);i++){bytes(&table[i].key,sizeof table[i].key);bytes(&table[i].data,sizeof table[i].data);}
    return digest;
}
static void reset(void){
    T_CLEAR();memset(workers,0,sizeof workers);atomic_store(&stopped,0);deadline=UINT64_MAX;
#if DEV
    atomic_store(&searched,0);limit=0;max_depth=4;
#endif
    T_START(&position);game_keys[0]=position.h;game_length=1;
    workers[0].keys[0]=position.h;workers[0].length=1;
}
/* Fixture setup only. It uses the actual pinned key/eval/EP helpers, while
 * independent Python Board supplies legal moves and exact quiet minimax. */
static void fixture(const char *fen){
    Board b={0};b.s=1;b.e=-1;int q=112;
    while(*fen!=' '){char c=*fen++;if(c=='/')q-=24;else if(c>='1'&&c<='8')q+=c-'0';else{
        const char *p=strchr("pnbrqk",tolower((unsigned char)c));assert(p);int v=(int)(p-"pnbrqk")+1;
        T_PUT(&b,q++,c>='a'&&c<='z'?-v:v);
    }}
    b.s=*++fen=='w'?1:-1;fen+=2;
    while(*fen!=' '){char c=*fen++;if(c=='K')b.c|=1;if(c=='Q')b.c|=2;if(c=='k')b.c|=4;if(c=='q')b.c|=8;}
    fen++;if(*fen!='-')b.e=fen[0]-'a'+16*(fen[1]-'1');while(*fen!=' ')fen++;b.half=atoi(fen+1);
    T_EP(&b);b.h^=T_STATE(&b);b.r=b.h;position=b;game_keys[0]=b.h;game_length=1;
    workers[0].keys[0]=b.h;workers[0].length=1;
}
static uint64_t key(const Board *b){return b->h^T_MIX(b->r+(unsigned)b->half);}
static uint64_t packed(int depth,int score,int bound){return ((uint64_t)(uint16_t)score<<17)|((uint64_t)depth<<33)|((uint64_t)bound<<41);}
static void emit(const char *group,int index,int score,Move move,Worker *w){
    printf("{\"group\":\"%s\",\"index\":%d,\"score\":%d,\"move\":%u,\"nodes\":%llu,\"length\":%d,\"state\":\"%016llx\"}\n",
        group,index,score,move,(unsigned long long)w->nodes,w->length,(unsigned long long)state_digest(w));
}
static void windows(void){
    for(int i=0;i<CASE_COUNT;i++){
        reset();fixture(cases[i].fen);Worker *w=workers;Move move=0;
        int score=query(w,&position,cases[i].depth,cases[i].beta,0,6,&move);
        assert(!atomic_load(&stopped));assert(w->length==1);
        emit("window",i,score,move,w);
    }
}
static void tt_contract(void){
    reset();Worker *w=workers;uint64_t k=key(&position);Move move=0;
    T_PROBE(k,packed(2,1234,1));assert(query(w,&position,2,1234,1,6,0)==1234);
    T_CLEAR();T_PROBE(k,packed(3,1234,1));assert(query(w,&position,2,1234,1,6,0)!=1234);
    T_CLEAR();T_PROBE(k,packed(2,1234,1));assert(query(w,&position,0,1234,1,6,0)!=1234);
    T_CLEAR();T_PROBE(k,packed(0,1234,1));assert(query(w,&position,0,1234,1,6,0)==1234);
    T_CLEAR();T_PROBE(k,packed(2,MATE-5,1));assert(query(w,&position,2,MATE-12,7,6,0)==MATE-12);
    T_CLEAR();T_PROBE(k,packed(2,-MATE+5,1));assert(query(w,&position,2,-MATE+12,7,6,0)==-MATE+12);
    T_CLEAR();T_PROBE(k,packed(1,1234,1));assert(query(w,&position,1,1234,0,6,&move)!=1234&&move);
    /* Actual directional records must still be admitted under unit windows. */
    T_CLEAR();T_PROBE(k,packed(2,100,2));assert(query(w,&position,2,100,1,6,0)==100);
    T_CLEAR();T_PROBE(k,packed(2,-100,3));assert(query(w,&position,2,-99,1,6,0)==-100);
    emit("tt",0,0,move,w);
}
static void contexts(void){
    reset();fixture("7k/8/8/8/8/8/1Q6/K7 w - - 99 1");uint64_t h=position.h,k=key(&position);Move move=0;
    int first=query(workers,&position,3,1,0,6,&move);assert(first==0);emit("half",0,first,move,workers);
    fixture("7k/8/8/8/8/8/1Q6/K7 w - - 0 1");assert(position.h==h&&key(&position)!=k);
    int second=query(workers,&position,3,1,0,6,&move);assert(second>0);emit("half",1,second,move,workers);
    reset();uint64_t original=key(&position);Board b;const char *names[]={"g1f3","g8f6","f3g1","f6g8"};
    for(int i=0;i<8;i++){
        Move list[MOVES];int n=T_GEN(&position,list),chosen=0;const char *s=names[i%4];
        Move wanted=MOVE(s[0]-'a'+16*(s[1]-'1'),s[2]-'a'+16*(s[3]-'1'),0);
        for(int j=0;j<n;j++)if(list[j]==wanted&&T_MAKE(&position,list[j],&b))chosen=1;
        assert(chosen);position=b;game_keys[game_length++]=position.h;
    }
    assert(position.h==game_keys[0]&&key(&position)!=original);
    workers[0].length=game_length;memcpy(workers[0].keys,game_keys,game_length*sizeof *game_keys);
    assert(query(workers,&position,3,1,0,6,&move)==0);emit("repeat",0,0,move,workers);
    /* Two reversible paths with the same board/half differ in TT context. */
    Board copy=position;copy.r=T_MIX(copy.r^1);assert(copy.h==position.h&&copy.half==position.half&&key(&copy)!=key(&position));
    reset();Worker *w=workers;Move a=MOVE(20,36,0),c=MOVE(19,35,0);
    int old=T_QUIET_SCORE(w,&position,a,6),other=T_QUIET_SCORE(w,&position,c,6);w->correction[(position.h^a)&1023]=16384;
    assert(T_QUIET_SCORE(w,&position,a,6)==old+256&&T_QUIET_SCORE(w,&position,c,6)==other);
    emit("ordering",0,0,a,w);
}
#if DEV
static void iterations(void){
    for(int i=0;i<3;i++){
        reset();fixture(quiet_fens[i]);Worker *w=workers;
        for(int repeat=0;repeat<4;repeat++){
            max_depth=(int[]){3,3,1,2}[repeat];w->best=0;T_THINK(w,&position);
            assert(!atomic_load(&stopped)&&w->depth==max_depth);emit("iteration",i*4+repeat,w->score,w->best,w);
        }
    }
    reset();Worker *active=workers;max_depth=4;T_THINK(active,&position);T_THINK(active,&position);
    assert(!atomic_load(&stopped)&&active->depth==4&&active->pvs&&active->qs&&active->hits&&active->hist_updates&&active->cont_updates&&active->corr_updates&&active->corr_uses);
    assert(active->f_probes>active->f_converged&&active->f_lower&&active->f_upper&&active->f_conflicts==0);
    emit("features",0,active->score,active->best,active);
    reset();Worker *w=workers;max_depth=1;T_THINK(w,&position);
    Move best=w->best;int score=w->score;uint64_t completed=w->nodes;
    assert(w->depth==1&&best);
    reset();w=workers;max_depth=20;limit=completed+1;T_THINK(w,&position);
    assert(atomic_load(&stopped)&&w->depth==1&&w->best==best&&w->score==score&&w->nodes==limit);
    emit("abort",0,w->score,w->best,w);
}
#endif
int main(void){
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);
#if DEV && PLY==4
    reset();max_depth=2;T_THINK(workers,&position);Board b;
    assert(atomic_load(&stopped)&&workers[0].depth==1&&workers[0].best&&workers[0].ply_aborts&&T_MAKE(&position,workers[0].best,&b));
    emit("ply4",0,workers[0].score,workers[0].best,workers);
#else
    windows();tt_contract();contexts();
#if DEV
    iterations();
#endif
#endif
    free(table);return 0;
}
