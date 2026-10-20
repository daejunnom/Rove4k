#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../c/parallel.h"
enum { SETTLES, NO_REFUTATION, REPEATED_REFUTATION, INCOMPLETE_CLAUSE,
       WRONG_FIRST, WRONG_REPLY, WRONG_DEPTH, WRONG_CONTEXT, REPAIR_CANCELLED,
       FOLLOWUP_INCOMPLETE, FOLLOWUP_WRONG_REPLY, STOP_DURING_REVIEW,
       LOWER_REPAIR, NO_REPLY };
typedef struct {
    _Atomic int active,peak,calls,repair_hint,stop_after,stopped,reviews,lower_alpha;
    int scenario,score_offset;
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
    r.generation=t->generation;r.depth=t->depth;
    r.score=t->first?400-(int)t->first*10+c->score_offset:10+(int)id;
    if(t->kind==ROVE_SELECT_REPLY)r.reply=c->scenario==NO_REPLY?0:43;
    if(t->kind==ROVE_COUNTERREPLY) {
        int review=atomic_fetch_add(&c->reviews,1);
        r.reply=t->reply;
        r.score=t->beta-((review==0 && c->scenario!=NO_REFUTATION) || c->scenario==REPEATED_REFUTATION);
        if(c->scenario==INCOMPLETE_CLAUSE || (review && c->scenario==FOLLOWUP_INCOMPLETE))r.complete=0;
        if(c->scenario==WRONG_FIRST)r.first++;
        if(c->scenario==WRONG_REPLY || (review && c->scenario==FOLLOWUP_WRONG_REPLY))r.reply++;
        if(c->scenario==WRONG_DEPTH)r.depth++;
        if(c->scenario==WRONG_CONTEXT)r.generation++;
        if(c->scenario==STOP_DURING_REVIEW)atomic_store(&c->stopped,1);
    }
    if(t->kind==ROVE_REPAIR) {
        assert(t->first==1 && t->reply==43 && t->generation==7 && t->depth==4);
        atomic_store(&c->repair_hint,(int)t->reply);
        if(c->scenario==LOWER_REPAIR)r.score=100;
        if(c->scenario==REPAIR_CANCELLED)r.complete=0;
    }
    if(t->kind==ROVE_NORMAL && t->first==2 && c->scenario==LOWER_REPAIR && t->alpha==100)
        atomic_store(&c->lower_alpha,1);
    r.bound=r.score<=t->alpha?ROVE_UPPER:r.score>=t->beta?ROVE_LOWER:ROVE_EXACT;
    atomic_fetch_sub(&c->active,1);
    return r;
}
static void predicates(void) {
    RoveTask t={1,0,4,-1000,1000,ROVE_NORMAL,0,7,1};
    RoveCompleted c={t,{.score=100,.bound=ROVE_EXACT,.complete=1,.first=1,.reply=2,.nodes=100,.generation=7,.depth=4}};
    assert(rove_parallel_reusable(&c,&t));
    t.generation++;assert(!rove_parallel_reusable(&c,&t));t.generation--;
    t.depth++;assert(!rove_parallel_reusable(&c,&t));t.depth--;
    c.result.generation++;assert(!rove_parallel_reusable(&c,&t));c.result.generation--;
    c.result.depth++;assert(!rove_parallel_reusable(&c,&t));c.result.depth--;
    c.task.kind=ROVE_COUNTERREPLY;assert(!rove_parallel_reusable(&c,&t));
    c.task.kind=ROVE_SELECT_REPLY;assert(!rove_parallel_reusable(&c,&t));c.task.kind=ROVE_NORMAL;
    c.result.bound=ROVE_UPPER;t.alpha=101;assert(rove_parallel_reusable(&c,&t));t.alpha=99;assert(!rove_parallel_reusable(&c,&t));
    c.result.bound=ROVE_LOWER;t.beta=99;assert(rove_parallel_reusable(&c,&t));t.beta=101;assert(!rove_parallel_reusable(&c,&t));
    t=(RoveTask){1,43,4,389,390,ROVE_COUNTERREPLY,0,7,1};
    RoveResult r={.score=389,.bound=ROVE_UPPER,.complete=1,.first=1,.reply=43,.generation=7,.depth=4};
    assert(rove_parallel_refutes(&t,&r,390));
    r.bound=ROVE_EXACT;assert(rove_parallel_refutes(&t,&r,390));
    r.bound=ROVE_LOWER;assert(!rove_parallel_refutes(&t,&r,390));
    r.bound=ROVE_UPPER;r.score=390;assert(!rove_parallel_refutes(&t,&r,390));r.score=389;
    r.complete=0;assert(!rove_parallel_refutes(&t,&r,390));r.complete=1;
    r.first++;assert(!rove_parallel_refutes(&t,&r,390));r.first--;
    r.reply++;assert(!rove_parallel_refutes(&t,&r,390));r.reply--;
    r.depth++;assert(!rove_parallel_refutes(&t,&r,390));r.depth--;
    r.generation++;assert(!rove_parallel_refutes(&t,&r,390));r.generation--;
    /* Even a refuting clause/selector can never enter the normal cache. */
    RoveParallel p={0};RoveCompleted slot={0};p.completed=&slot;
    assert(!pthread_mutex_init(&p.mutex,0));
    rove_parallel_accept(&p,0,t,r);assert(!slot.result.complete);
    t.kind=ROVE_SELECT_REPLY;rove_parallel_accept(&p,0,t,r);assert(!slot.result.complete);
    pthread_mutex_destroy(&p.mutex);
}
int main(void) {
    predicates();
    uint32_t moves[32];for(unsigned i=0;i<32;i++)moves[i]=i+1;
    for(int mode=0;mode<=4;mode++) {
        Context ctx={0};RoveParallelHistory h={0};
        RoveParallelResult r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,mode,7,&h);
        assert(r.completedall && r.best.complete && r.best.bound==ROVE_EXACT);
        assert(r.best.first==(mode?1:2));assert(r.best.score==(mode?390:10));
        assert(atomic_load(&ctx.active)==0 && atomic_load(&ctx.peak)>1);
        if(mode==1 || mode==2)assert(r.reused && r.reassigned);
        if(mode==2)assert(r.groups==2 && r.shared_bounds>0);
        if(mode==3)assert(r.clauses==2 && r.repairs==1 && atomic_load(&ctx.repair_hint)==43);
        if(mode==4)assert(r.mode==2);
        printf("mode=%d selected=%d assigned=%llu reused=%llu shared=%llu clauses=%llu repairs=%llu peak=%d\n",mode,r.mode,(unsigned long long)r.assigned,(unsigned long long)r.reused,(unsigned long long)r.shared_bounds,(unsigned long long)r.clauses,(unsigned long long)r.repairs,atomic_load(&ctx.peak));
    }
    for(int scenario=NO_REFUTATION;scenario<=NO_REPLY;scenario++) {
        Context ctx={0};ctx.scenario=scenario;RoveParallelHistory h={.first=9,.score=123,.depth=3};
        RoveParallelResult r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,3,7,&h);
        int success=scenario==NO_REFUTATION || scenario==LOWER_REPAIR || scenario==NO_REPLY;
        assert(!!r.completedall==success && !!r.best.complete==success);
        assert(atomic_load(&ctx.active)==0);
        if(!success)assert(h.first==9 && h.score==123 && h.depth==3);
        if(scenario==NO_REFUTATION)assert(r.clauses==1 && r.repairs==0 && r.best.score==390);
        if(scenario==REPEATED_REFUTATION)assert(r.clauses==2 && r.repairs==1);
        if(scenario==LOWER_REPAIR)assert(r.best.first==2 && r.best.score==380 && atomic_load(&ctx.lower_alpha));
        if(scenario==NO_REPLY)assert(!r.clauses && !r.repairs);
        printf("pals-case=%d completed=%d clauses=%llu repairs=%llu\n",scenario,r.completedall,(unsigned long long)r.clauses,(unsigned long long)r.repairs);
    }
    Context ctx={0};RoveParallelHistory h={.first=1,.reply=42,.score=0,.depth=3,.total_ns=100000000};
    RoveParallelResult r=rove_parallel_search(search,&ctx,moves,32,4,-1000,1000,1,42,stopped,8,4,7,&h);
    assert(r.mode==3 && r.repairs==1 && r.best.score==390);
    memset(&ctx,0,sizeof(ctx));
    r=rove_parallel_search(search,&ctx,moves,32,4,400,1000,1,42,stopped,8,3,7,&h);
    assert(r.completedall && r.best.bound==ROVE_UPPER && !r.clauses && !r.repairs);
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
