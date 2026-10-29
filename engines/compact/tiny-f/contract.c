/* Compile against one frozen DEV/main.c using -I that actual build directory.
 * The fixture includes real static TT, ordering and search functions. */
#define main tiny_f_uci_main
#include "main.c"
#undef main
#include <assert.h>
#if TINY_F_STRUCTURED
#define record(k,w,d) probe((k),(w)?(d):0)
#else
#define record(k,w,d) probe((k),(w),(d))
#endif

static void reset_contract(void){
    clear();memset(workers,0,sizeof workers);atomic_store(&stopped,0);
    atomic_store(&searched,0);limit=0;deadline=UINT64_MAX;
    start(&position);game_keys[0]=position.h;game_length=1;
    workers[0].length=1;workers[0].keys[0]=position.h;
}
static uint64_t test_data(int depth,int score,int bound){
    return ((uint64_t)(uint16_t)score<<17)|((uint64_t)depth<<33)|((uint64_t)bound<<41);
}
static void horizon_contract(void){
    reset_contract();Worker *w=workers;
    uint64_t key=position.h^mix(position.r+(unsigned)position.half);
    record(key,1,test_data(2,1234,1));
    assert(search(w,&position,2,-MATE,MATE,1,0,0)==1234);
    clear();record(key,1,test_data(3,1234,1));
    assert(search(w,&position,2,-MATE,MATE,1,0,0)!=1234);
    clear();record(key,1,test_data(2,1234,1));
    assert(search(w,&position,0,-MATE,MATE,1,0,0)!=1234);
    clear();record(key,1,test_data(0,1234,1));
    assert(search(w,&position,0,-MATE,MATE,1,0,0)==1234);
    clear();record(key,1,test_data(2,MATE-5,1));
    assert(search(w,&position,2,-MATE,MATE,7,0,0)==MATE-12);
    clear();record(key,1,test_data(2,-MATE+5,1));
    assert(search(w,&position,2,-MATE,MATE,7,0,0)==-MATE+12);
    /* Root never accepts even a matching exact record without a searched move. */
    Move move=0;clear();record(key,1,test_data(1,1234,1));
    assert(search(w,&position,1,-MATE,MATE,0,0,&move)!=1234&&move);
}
static void ordering_contract(void){
    reset_contract();Worker *w=workers;
    Move a=MOVE(20,36,0),b=MOVE(19,35,0);
    int old_a=quiet_score(w,&position,a,6),old_b=quiet_score(w,&position,b,6);
    assert(((position.h^a)&1023)!=((position.h^b)&1023));
    w->correction[(position.h^a)&1023]=16384;
    assert(quiet_score(w,&position,a,6)==old_a+256);
    assert(quiet_score(w,&position,b,6)==old_b);
    assert(quiet_score(w,&position,a,6)>quiet_score(w,&position,b,6));
    assert(w->corr_uses>0);
}
static void locking_contract(void){
    reset_contract();uint64_t key=17,data=UINT64_C(0x987654321);
    record(key,1,data);assert(record(key,0,0)==data);
    assert(record(key+((uint64_t)1<<TT_BITS),0,0)==0);
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    assert(!atomic_flag_test_and_set(&e->lock));
    assert(record(key,0,0)==0);record(key,1,data+1);
    atomic_flag_clear(&e->lock);assert(record(key,0,0)==data);
}
static atomic_uint_fast64_t observed;
static uint64_t parity_digest=UINT64_C(1469598103934665603),parity_nodes;
static void digest_bytes(const void *bytes,size_t length){
    const unsigned char *p=bytes;while(length--)parity_digest=(parity_digest^*p++)*UINT64_C(1099511628211);
}
static void parity_contract(void){
    const char *positions[]={
        "8/6pk/8/8/8/8/PK6/8 w - - 0 1",
        "8/6pk/8/8/8/P7/1K6/8 b - - 0 1",
        "8/7k/6p1/8/8/P7/1K6/8 w - - 0 1",
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 1",
        "7k/8/8/8/8/8/1Q6/K7 w - - 99 1",
        "7k/8/8/8/8/8/1Q6/K7 w - - 0 1",
        "7k/P7/8/8/8/8/8/K7 w - - 0 1",
        "7k/8/5b2/8/8/8/1B6/K7 w - - 0 1",
        "7k/8/8/8/8/8/1NN5/K7 w - - 0 1",
        "7k/6Q1/5K2/8/8/8/8/8 b - - 100 1",
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"};
    reset_contract();Worker *w=workers;
    for(int n=0;n<12;n++){
        assert(fen(&position,positions[n]));game_keys[0]=position.h;
        for(int repeat=0;repeat<3;repeat++){
            max_depth=(int[]){3,1,2}[repeat];w->best=0;think(w,&position);
            assert(!atomic_load(&stopped)&&w->depth==max_depth);parity_nodes+=w->nodes;
            digest_bytes(&w->best,sizeof w->best);digest_bytes(&w->score,sizeof w->score);
            digest_bytes(&w->nodes,sizeof w->nodes);
            digest_bytes(w->history,sizeof w->history);digest_bytes(w->continuation,sizeof w->continuation);
            digest_bytes(w->correction,sizeof w->correction);
            for(int i=0;i<(1<<TT_BITS);i++){
                digest_bytes(&table[i].key,sizeof table[i].key);digest_bytes(&table[i].data,sizeof table[i].data);
            }
        }
    }
}
static void *stress(void *argument){
    uintptr_t id=(uintptr_t)argument;
    uint64_t key=(id<<TT_BITS)|17,data=key^UINT64_C(0xa185ab93ce78142f);
    for(int i=0;i<20000;i++){
        record(key,1,data);uint64_t got=record(key,0,0);
        assert(!got||got==data);if(got)atomic_fetch_add(&observed,1);
    }
    return 0;
}
static void publication_contract(void){
    reset_contract();pthread_t threads[8];
    for(uintptr_t i=0;i<8;i++)assert(!pthread_create(threads+i,0,stress,(void *)i));
    for(int i=0;i<8;i++)assert(!pthread_join(threads[i],0));
    assert(atomic_load(&observed)>0);
}
static void interrupted_contract(void){
    reset_contract();Worker *w=workers;max_depth=1;think(w,&position);
    Move best=w->best;int score=w->score;
    assert(best&&w->depth==1&&w->f_converged==1);
    /* A budget above one converged depth, below the next, must preserve it. */
    uint64_t first_nodes=w->nodes;
    reset_contract();w=workers;max_depth=20;limit=first_nodes+1;think(w,&position);
    assert(atomic_load(&stopped)&&w->depth==1&&w->best==best&&w->score==score);
    assert(w->nodes==limit&&w->f_probes>w->f_converged);
    printf("{\"passed\":true,\"stress_puts\":160000,\"stress_reads\":160000,\"observed_matching_reads\":%llu,\"cancel_nodes\":%llu,\"state_cases\":36,\"state_nodes\":%llu,\"state_digest\":\"%016llx\"}\n",
           (unsigned long long)atomic_load(&observed),(unsigned long long)w->nodes,
           (unsigned long long)parity_nodes,(unsigned long long)parity_digest);
}
int main(void){
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);
#if PLY == 4
    reset_contract();max_depth=2;think(workers,&position);
    assert(atomic_load(&stopped)&&workers[0].depth==1&&workers[0].best&&workers[0].ply_aborts);
    Board child;assert(make(&position,workers[0].best,&child));
    printf("{\"passed\":true,\"completed_depth\":%d,\"ply_aborts\":%llu,\"legal_witness\":true}\n",
           workers[0].depth,(unsigned long long)workers[0].ply_aborts);
#else
    horizon_contract();ordering_contract();locking_contract();parity_contract();publication_contract();interrupted_contract();
#endif
    free(table);return 0;
}
