/* Focused actual F DEV driver witness. Engine bodies are included unchanged.
 * Fixture resets model fresh jobs; no preseeded old best is retained. */
#define main frozen_entry_main
#include ENGINE_SOURCE
#undef main
#include <assert.h>

static const char quiet_fen[]="8/6pk/8/8/8/8/PK6/8 w - - 0 1";
static void reset_job(void){
    clear();memset(workers,0,sizeof workers);atomic_store(&stopped,0);
    atomic_store(&searched,0);limit=0;max_depth=1;deadline=UINT64_MAX;
    start(&position);game_keys[0]=position.h;game_length=1;
}
static uint64_t state_digest(Worker *w){
    uint64_t hash=UINT64_C(1469598103934665603);
    const unsigned char *p=(const unsigned char *)w->history;
    for(size_t i=0;i<sizeof w->history;i++)hash=(hash^p[i])*UINT64_C(1099511628211);
    p=(const unsigned char *)w->continuation;
    for(size_t i=0;i<sizeof w->continuation;i++)hash=(hash^p[i])*UINT64_C(1099511628211);
    p=(const unsigned char *)w->correction;
    for(size_t i=0;i<sizeof w->correction;i++)hash=(hash^p[i])*UINT64_C(1099511628211);
    for(int i=0;i<w->length;i++)hash=(hash^w->keys[i])*UINT64_C(1099511628211);
    for(int i=0;i<(1<<TT_BITS);i++){
        hash=(hash^table[i].key)*UINT64_C(1099511628211);
        hash=(hash^table[i].data)*UINT64_C(1099511628211);
    }
    return hash;
}
static void row(Worker *w){
    Board child;assert(w->best&&make(&position,w->best,&child)&&verify_board(&child));
    assert(w->length==game_length&&w->keys[0]==position.h);
    printf("{\"depth\":%d,\"score\":%d,\"move\":%u,\"nodes\":%llu,\"searched\":%llu,"
        "\"stopped\":%d,\"f_probes\":%llu,\"f_lower\":%llu,\"f_upper\":%llu,"
        "\"f_converged\":%llu,\"f_conflicts\":%llu,\"f_upper_other\":%llu,"
        "\"state\":\"%016llx\"}",w->depth,w->score,w->best,
        (unsigned long long)w->nodes,(unsigned long long)atomic_load(&searched),atomic_load(&stopped),
        (unsigned long long)w->f_probes,(unsigned long long)w->f_lower,(unsigned long long)w->f_upper,
        (unsigned long long)w->f_converged,(unsigned long long)w->f_conflicts,(unsigned long long)w->f_upper_other,
        (unsigned long long)state_digest(w));
}
int main(void){
    assert(DEV==1&&WORKERS==2&&TT_BITS==18&&PLY==128&&sizeof(Board)==176);
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);
    reset_job();assert(fen(&position,quiet_fen)&&verify_board(&position));
    game_keys[0]=position.h;max_depth=3;think(workers,&position);
    assert(!atomic_load(&stopped)&&workers[0].depth==3&&workers[0].f_converged==3);
    assert(workers[0].f_lower&&workers[0].f_upper&&!workers[0].f_conflicts);
    printf("{\"passed\":true,\"DEV\":1,\"board_bytes\":176,\"quiet\":");row(workers);

    reset_job();think(workers,&position);
    assert(!atomic_load(&stopped)&&workers[0].depth==1&&workers[0].f_converged==1);
    Move best=workers[0].best;int score=workers[0].score;uint64_t completed=workers[0].nodes;
    assert(best&&completed&&completed<UINT64_MAX);
    printf(",\"completed_one\":");row(workers);

    reset_job();max_depth=20;limit=completed+1;think(workers,&position);
    assert(atomic_load(&stopped)&&workers[0].depth==1&&workers[0].best==best&&workers[0].score==score);
    assert(workers[0].nodes==limit&&atomic_load(&searched)==limit&&workers[0].f_converged==1&&!workers[0].f_conflicts);
    printf(",\"interrupted\":");row(workers);
    printf(",\"limit\":%llu,\"same_job_completed_iteration_retained\":true}\n",(unsigned long long)limit);
    free(table);return 0;
}
