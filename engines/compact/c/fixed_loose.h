#ifndef ROVE_COMPACT_LOOSE_H
#define ROVE_COMPACT_LOOSE_H
/* Fixed Loose-SMP specialization of parallel.h mode 0.  The coordinator is
 * worker zero; every helper exists before UCI and searches the complete root.
 * Complete results use the same lowest-worker-index precedence as mode 0.
 * This header does not implement root splitting, grouping or PALS. */
#include <stdlib.h>
#include <stdio.h>

enum { ROVE_EXACT, ROVE_LOWER, ROVE_UPPER };
enum { ROVE_NORMAL, ROVE_COUNTERREPLY, ROVE_REPAIR };
typedef struct {
    uint32_t first,reply;
    int depth,alpha,beta,kind,group;
    uint64_t generation;
    int groups;
} RoveTask;
typedef struct {
    int score,bound,complete;
    uint32_t first,reply;
    uint64_t nodes;
} RoveResult;
typedef RoveResult (*RoveSearch)(void *,const RoveTask *,unsigned);
typedef int (*RoveStopped)(void *);
typedef struct {
    uint32_t first,reply;
    int score,depth;
    uint64_t proposal_ns,total_ns,nodes;
} RoveParallelHistory;
typedef struct {
    RoveResult best;
    int completedall,mode,groups;
    uint64_t assigned,reassigned,reused,shared_bounds,clauses,repairs;
} RoveParallelResult;
static struct {
    pthread_mutex_t mutex;
    pthread_cond_t ready,done;
    pthread_t threads[ROVE_WORKERS];
    unsigned ids[ROVE_WORKERS],finished;
    _Atomic unsigned assigned;
    uint64_t epoch;
    int initialized,quit,busy;
    RoveTask task;
    RoveSearch search;
    RoveStopped stopped;
    void *context;
    RoveResult results[ROVE_WORKERS];
} rove_loose;

static void rove_loose_invoke(unsigned id) {
    RoveResult result={0};
    if(!rove_loose.stopped(rove_loose.context)) {
        atomic_fetch_add_explicit(&rove_loose.assigned,1,memory_order_relaxed);
        result=rove_loose.search(rove_loose.context,&rove_loose.task,id);
    }
    /* This slot has exactly one writer. The completion barrier below makes
     * it visible before the coordinator reads or reuses any callback state. */
    rove_loose.results[id]=result;
}
static void *rove_loose_helper(void *arg) {
    unsigned id=*(unsigned *)arg;
    uint64_t seen=0;
    pthread_mutex_lock(&rove_loose.mutex);
    while(!rove_loose.quit) {
        while(!rove_loose.quit&&seen==rove_loose.epoch)
            pthread_cond_wait(&rove_loose.ready,&rove_loose.mutex);
        if(rove_loose.quit)break;
        seen=rove_loose.epoch;
        pthread_mutex_unlock(&rove_loose.mutex);
        rove_loose_invoke(id);
        pthread_mutex_lock(&rove_loose.mutex);
        if(++rove_loose.finished==ROVE_WORKERS-1)
            pthread_cond_broadcast(&rove_loose.done);
    }
    pthread_mutex_unlock(&rove_loose.mutex);
    return 0;
}
static void rove_loose_join(pthread_t thread) {
    if(pthread_join(thread,0))abort();
}
static int rove_parallel_init(int workers) {
    if(workers!=ROVE_WORKERS)return 0;
    if(rove_loose.initialized)return 1;
    if(pthread_mutex_init(&rove_loose.mutex,0))return 0;
    if(pthread_cond_init(&rove_loose.ready,0))goto mutex;
    if(pthread_cond_init(&rove_loose.done,0))goto ready;
    rove_loose.epoch=0;rove_loose.quit=0;rove_loose.busy=0;
    unsigned i;
    for(i=1;i<ROVE_WORKERS;i++) {
        rove_loose.ids[i]=i;
        if(pthread_create(&rove_loose.threads[i],0,rove_loose_helper,&rove_loose.ids[i])) {
            pthread_mutex_lock(&rove_loose.mutex);
            rove_loose.quit=1;
            pthread_cond_broadcast(&rove_loose.ready);
            pthread_mutex_unlock(&rove_loose.mutex);
            while(--i)rove_loose_join(rove_loose.threads[i]);
            pthread_cond_destroy(&rove_loose.done);
            goto ready;
        }
    }
    rove_loose.initialized=1;
    return 1;
ready:
    pthread_cond_destroy(&rove_loose.ready);
mutex:
    pthread_mutex_destroy(&rove_loose.mutex);
    return 0;
}
static void rove_parallel_shutdown(void) {
    if(!rove_loose.initialized)return;
    pthread_mutex_lock(&rove_loose.mutex);
    while(rove_loose.busy)pthread_cond_wait(&rove_loose.done,&rove_loose.mutex);
    rove_loose.quit=1;
    pthread_cond_broadcast(&rove_loose.ready);
    pthread_mutex_unlock(&rove_loose.mutex);
    for(unsigned i=1;i<ROVE_WORKERS;i++)rove_loose_join(rove_loose.threads[i]);
    pthread_cond_destroy(&rove_loose.done);
    pthread_cond_destroy(&rove_loose.ready);
    pthread_mutex_destroy(&rove_loose.mutex);
    rove_loose.initialized=0;
}
static RoveParallelResult rove_parallel_search(RoveSearch search,void *context,
        const uint32_t *moves,int n,int depth,int alpha,int beta,
        uint32_t priorfirst,uint32_t priorreply,RoveStopped stopped,
        int workers,int mode,uint64_t generation,RoveParallelHistory *history) {
    RoveParallelResult result={0};result.groups=1;
    (void)moves;(void)n;(void)priorfirst;(void)priorreply;(void)history;
    if(mode||workers!=ROVE_WORKERS||alpha>=beta||stopped(context))return result;
    if(!rove_loose.initialized)abort();
    pthread_mutex_lock(&rove_loose.mutex);
    if(rove_loose.busy)abort();
    rove_loose.busy=1;rove_loose.finished=0;
    atomic_store_explicit(&rove_loose.assigned,0,memory_order_relaxed);
    rove_loose.search=search;rove_loose.stopped=stopped;rove_loose.context=context;
    rove_loose.task=(RoveTask){0,0,depth,alpha,beta,ROVE_NORMAL,0,generation,1};
    rove_loose.epoch++;
    pthread_cond_broadcast(&rove_loose.ready);
    pthread_mutex_unlock(&rove_loose.mutex);
    rove_loose_invoke(0);
    pthread_mutex_lock(&rove_loose.mutex);
    while(rove_loose.finished<ROVE_WORKERS-1)
        pthread_cond_wait(&rove_loose.done,&rove_loose.mutex);
    for(unsigned i=0;i<ROVE_WORKERS;i++) {
        RoveResult r=rove_loose.results[i];
        if(r.complete&&(r.bound==ROVE_EXACT||
           (r.bound==ROVE_LOWER&&r.score>=beta)||
           (r.bound==ROVE_UPPER&&r.score<=alpha))) {
            result.best=r;result.completedall=1;break;
        }
    }
    result.assigned=atomic_load_explicit(&rove_loose.assigned,memory_order_relaxed);
    rove_loose.busy=0;
    pthread_cond_broadcast(&rove_loose.done);
    pthread_mutex_unlock(&rove_loose.mutex);
    return result;
}
#endif
