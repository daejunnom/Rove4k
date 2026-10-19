#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "parallel.h"
typedef struct {
    _Atomic int active,peak,calls,repair_hint,stop_after,stopped;
    int score_offset;
} Context;
static int stopped(void *arg) {
    Context *c=arg;
    int limit=atomic_load(&c->stop_after);
    return atomic_load(&c->stopped) || (limit && atomic_load(&c->calls)>=limit);
}
static RoveResult search(void *arg,const RoveTask *t,unsigned id) {
    Context *c=arg;
    assert(t->alpha<t->beta);
    if(stopped(c))return (RoveResult){0};
    int live=atomic_fetch_add(&c->active,1)+1;
    int peak=atomic_load(&c->peak);
    while(peak<live && !atomic_compare_exchange_weak(&c->peak,&peak,live)){}
    atomic_fetch_add(&c->calls,1);
    struct timespec delay={0,1000000};nanosleep(&delay,0);
    RoveResult r={0};r.first=t->first?t->first:2;r.reply=42;r.nodes=1;r.complete=1;
    r.score=t->first?400-(int)t->first*10+c->score_offset:10+(int)id;
    if(t->kind==ROVE_COUNTERREPLY) {r.reply=43+id;r.score=-999;}
    if(t->kind==ROVE_REPAIR)atomic_store(&c->repair_hint,(int)t->reply);
    r.bound=r.score<=t->alpha?ROVE_UPPER:r.score>=t->beta?ROVE_LOWER:ROVE_EXACT;
    atomic_fetch_sub(&c->active,1);
    return r;
}
int main(void) {
    uint32_t moves[32];for(unsigned i=0;i<32;i++)moves[i]=i+1;
    RoveTask t={1,0,4,-1000,1000,ROVE_NORMAL,0,7};
    RoveCompleted c={t,{100,ROVE_EXACT,1,1,2,100}};
    assert(rove_parallel_reusable(&c,&t));
    t.generation++;assert(!rove_parallel_reusable(&c,&t));t.generation--;
    t.depth++;assert(!rove_parallel_reusable(&c,&t));t.depth--;
    c.task.kind=ROVE_COUNTERREPLY;assert(!rove_parallel_reusable(&c,&t));c.task.kind=ROVE_NORMAL;
    c.result.bound=ROVE_UPPER;t.alpha=101;assert(rove_parallel_reusable(&c,&t));t.alpha=99;assert(!rove_parallel_reusable(&c,&t));
    c.result.bound=ROVE_LOWER;t.beta=99;assert(rove_parallel_reusable(&c,&t));t.beta=101;assert(!rove_parallel_reusable(&c,&t));
    for(int mode=0;mode<=4;mode++) {
        Context ctx={0};RoveParallelHistory h={0};
        RoveParallelResult r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,mode,7,&h);
        assert(r.completedall && r.best.complete && r.best.bound==ROVE_EXACT);
        assert(r.best.first==(mode?1:2));assert(r.best.score==(mode?390:10));
        assert(atomic_load(&ctx.active)==0 && atomic_load(&ctx.peak)>1);
        if(mode==1 || mode==2)assert(r.reused && r.reassigned);
        if(mode==2)assert(r.groups==2 && r.shared_bounds>0);
        if(mode==3)assert(r.clauses==8 && r.repairs==1 && atomic_load(&ctx.repair_hint)>=43 && r.best.score==390);
        if(mode==4)assert(r.mode==2);
        printf("mode=%d selected=%d assigned=%llu reused=%llu shared=%llu clauses=%llu repairs=%llu peak=%d\n",mode,r.mode,(unsigned long long)r.assigned,(unsigned long long)r.reused,(unsigned long long)r.shared_bounds,(unsigned long long)r.clauses,(unsigned long long)r.repairs,atomic_load(&ctx.peak));
    }
    Context ctx={0};RoveParallelHistory h={.first=1,.reply=42,.score=0,.depth=3,.total_ns=100000000};
    RoveParallelResult r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,4,7,&h);
    assert(r.mode==3 && r.repairs==1 && r.best.score==390);
    memset(&ctx,0,sizeof(ctx));atomic_store(&ctx.stop_after,3);
    r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,1,7,&h);
    assert(!r.completedall && !r.best.complete && atomic_load(&ctx.active)==0);
    memset(&ctx,0,sizeof(ctx));
    r=rove_parallel_search(search,&ctx,moves,32,4,-1000,300,1,42,stopped,8,1,7,&h);
    assert(r.completedall && r.best.complete && r.best.bound==ROVE_LOWER && r.best.score==390);
    assert(atomic_load(&ctx.active)==0);
    /* A profile mismatch cannot silently run fewer helpers than requested. */
    r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,4,0,7,&h);
    assert(!r.completedall && !r.best.complete);
    rove_parallel_shutdown();
    assert(!rove_parallel_threads.initialized);
    assert(rove_parallel_init(1));
    r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,1,1,7,&h);
    assert(r.completedall && atomic_load(&ctx.active)==0);
    rove_parallel_shutdown();
    puts("parallel contracts passed");
}
