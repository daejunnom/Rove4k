#ifndef ROVE_PARALLEL_H
#define ROVE_PARALLEL_H
/* The context fixes position, evaluator and selective-search semantics for one
 * invocation. Only complete NORMAL/REPAIR results can update shared bounds.
 * COUNTERREPLY is a constrained diagnostic and is never a root-move bound. */
#include <stdint.h>
#include <stdlib.h>
#include <limits.h>
#include <stdatomic.h>
#include <pthread.h>
#include <time.h>
#include <stdio.h>
#include <string.h>

enum { ROVE_EXACT, ROVE_LOWER, ROVE_UPPER };
enum { ROVE_NORMAL, ROVE_COUNTERREPLY, ROVE_REPAIR, ROVE_SELECT_REPLY };
typedef struct {
    uint32_t first, reply;
    int depth, alpha, beta, kind, group;
    uint64_t generation;
    int groups;
} RoveTask;
typedef struct {
    int score, bound, complete;
    uint32_t first, reply;
    uint64_t nodes;
    uint64_t generation;
    int depth;
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
typedef struct { RoveTask task; RoveResult result; } RoveCompleted;
typedef struct {
    RoveSearch search;
    RoveStopped stopped;
    void *context;
    const uint32_t *moves;
    int n,depth,alpha,beta,workers,mode,groups,bestalpha,bestgroup;
    uint64_t generation;
    _Atomic unsigned next;
    pthread_mutex_t mutex;
    RoveCompleted *completed;
    RoveParallelResult result;
    _Atomic int resource_failed;
} RoveParallel;
typedef struct { RoveParallel *p; unsigned id; } RoveParallelWorker;

static uint64_t rove_parallel_clock(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;
}
static int rove_parallel_reusable(const RoveCompleted *c,const RoveTask *t) {
    const RoveTask *s=&c->task;
    const RoveResult *r=&c->result;
    return r->complete && (s->kind==ROVE_NORMAL || s->kind==ROVE_REPAIR) &&
        s->generation==t->generation && s->first==t->first &&
        s->depth==t->depth && r->generation==t->generation &&
        r->depth==t->depth && r->first==t->first &&
        (r->bound==ROVE_EXACT ||
         (r->bound==ROVE_LOWER && r->score>=t->beta) ||
         (r->bound==ROVE_UPPER && r->score<=t->alpha));
}
static int rove_parallel_valid(const RoveTask *t,const RoveResult *r) {
    return r->complete && r->generation==t->generation && r->depth==t->depth &&
        (!t->first || r->first==t->first) &&
        (r->bound==ROVE_EXACT ||
         (r->bound==ROVE_LOWER && r->score>=t->beta) ||
         (r->bound==ROVE_UPPER && r->score<=t->alpha));
}
static int rove_parallel_refutes(const RoveTask *t,const RoveResult *r,int claim) {
    /* A fixed reply challenges only the claimed score for this first move.
     * Its upper/exact bound is never a normal root bound or cached result. */
    return t->kind==ROVE_COUNTERREPLY && t->reply &&
        r->reply==t->reply && rove_parallel_valid(t,r) &&
        (r->bound==ROVE_EXACT || r->bound==ROVE_UPPER) && r->score<claim;
}
static void rove_parallel_accept(RoveParallel *p,int index,
                                  RoveTask task,RoveResult r) {
    if((task.kind!=ROVE_NORMAL && task.kind!=ROVE_REPAIR) ||
       !rove_parallel_valid(&task,&r))return;
    pthread_mutex_lock(&p->mutex);
    p->completed[index]=(RoveCompleted){task,r};
    if(r.bound!=ROVE_UPPER && r.score>p->bestalpha) {
        p->bestalpha=r.score;
        p->bestgroup=task.group;
    }
    pthread_mutex_unlock(&p->mutex);
}
static void *rove_parallel_worker(void *arg) {
    RoveParallelWorker *worker=arg;
    RoveParallel *p=worker->p;
    unsigned id=worker->id;
    unsigned jobs=0;
    if(p->mode==0) {
        if(atomic_load(&p->resource_failed) || p->stopped(p->context))return 0;
        RoveTask task={0,0,p->depth,p->alpha,p->beta,ROVE_NORMAL,0,p->generation,p->groups};
        RoveResult r=p->search(p->context,&task,id);
        pthread_mutex_lock(&p->mutex);
        p->result.assigned++;
        /* Whole-root searches may differ in ordering; worker number supplies
         * a stable tie break rather than selecting an optimistic high score. */
        if(rove_parallel_valid(&task,&r) &&
           (!p->result.completedall || (int)id<p->bestgroup)) {
            p->result.best=r;
            p->result.completedall=1;
            p->bestgroup=(int)id;
        }
        pthread_mutex_unlock(&p->mutex);
        return 0;
    }
    while(!atomic_load(&p->resource_failed) && !p->stopped(p->context)) {
        unsigned index=atomic_fetch_add(&p->next,1);
        if(index>=(unsigned)p->n)break;
        RoveTask task={p->moves[index],0,p->depth,p->alpha,p->beta,
                      ROVE_NORMAL,p->groups>1?(int)id/4:0,p->generation,p->groups};
        pthread_mutex_lock(&p->mutex);
        if(p->bestalpha>=p->beta) {
            pthread_mutex_unlock(&p->mutex);
            break;
        }
        task.alpha=p->bestalpha;
        if(p->groups>1 && p->bestalpha>p->alpha && p->bestgroup!=task.group)
            p->result.shared_bounds++;
        if(rove_parallel_reusable(&p->completed[index],&task)) {
            p->result.reused++;
            pthread_mutex_unlock(&p->mutex);
            continue;
        }
        p->result.assigned++;
        if(jobs++)p->result.reassigned++;
        pthread_mutex_unlock(&p->mutex);
        RoveResult r=p->search(p->context,&task,id);
        rove_parallel_accept(p,(int)index,task,r);
    }
    return 0;
}
typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t ready,done;
    pthread_t threads[511];
    unsigned ids[511],workers,finished;
    uint64_t epoch;
    int initialized,quit,root_busy;
    RoveParallel *job;
    RoveCompleted completed[256];
} RoveParallelPool;
static RoveParallelPool rove_parallel_threads;
static void *rove_parallel_helper(void *arg) {
    RoveParallelPool *pool=&rove_parallel_threads;
    unsigned id=*(unsigned *)arg;
    uint64_t seen=0;
    pthread_mutex_lock(&pool->mutex);
    for(;;) {
        while(!pool->quit && seen==pool->epoch)pthread_cond_wait(&pool->ready,&pool->mutex);
        if(pool->quit)break;
        seen=pool->epoch;
        RoveParallelWorker worker={pool->job,id};
        pthread_mutex_unlock(&pool->mutex);
        rove_parallel_worker(&worker);
        pthread_mutex_lock(&pool->mutex);
        if(++pool->finished==pool->workers-1)pthread_cond_broadcast(&pool->done);
    }
    pthread_mutex_unlock(&pool->mutex);
    return 0;
}
static void rove_parallel_join(pthread_t thread) {
    int error=pthread_join(thread,0);
    if(error) {
        fprintf(stderr,"Rove4k: cannot join search helper (%d)\n",error);
        abort(); /* Its state cannot safely be reclaimed after a failed join. */
    }
}
static int rove_parallel_init(int workers) {
    RoveParallelPool *pool=&rove_parallel_threads;
    if(workers<1 || workers>512) {
        fprintf(stderr,"Rove4k: invalid fixed worker count %d\n",workers);
        return 0;
    }
    if(pool->initialized) {
        if(pool->workers==(unsigned)workers)return 1;
        fprintf(stderr,"Rove4k: fixed pool has %u workers, requested %d\n",pool->workers,workers);
        return 0;
    }
    int error=pthread_mutex_init(&pool->mutex,0);
    if(error)goto failed_mutex;
    error=pthread_cond_init(&pool->ready,0);
    if(error)goto failed_ready;
    error=pthread_cond_init(&pool->done,0);
    if(error)goto failed_done;
    pool->workers=(unsigned)workers;pool->epoch=0;pool->quit=0;pool->job=0;pool->root_busy=0;
    unsigned started=0;
    for(int i=1;i<workers;i++) {
        pool->ids[i-1]=(unsigned)i;
        error=pthread_create(&pool->threads[i-1],0,rove_parallel_helper,&pool->ids[i-1]);
        if(error) {
            pthread_mutex_lock(&pool->mutex);
            pool->quit=1;
            pthread_cond_broadcast(&pool->ready);
            pthread_mutex_unlock(&pool->mutex);
            for(unsigned j=0;j<started;j++)rove_parallel_join(pool->threads[j]);
            pthread_cond_destroy(&pool->done);
            goto failed_done;
        }
        started++;
    }
    pool->initialized=1;
    return 1;
failed_done:
    pthread_cond_destroy(&pool->ready);
failed_ready:
    pthread_mutex_destroy(&pool->mutex);
failed_mutex:
    fprintf(stderr,"Rove4k: fixed search pool startup failed (%d)\n",error);
    return 0;
}
static void rove_parallel_shutdown(void) {
    RoveParallelPool *pool=&rove_parallel_threads;
    if(!pool->initialized)return;
    pthread_mutex_lock(&pool->mutex);
    while(pool->root_busy)pthread_cond_wait(&pool->done,&pool->mutex);
    pool->quit=1;
    pthread_cond_broadcast(&pool->ready);
    pthread_mutex_unlock(&pool->mutex);
    for(unsigned i=1;i<pool->workers;i++)rove_parallel_join(pool->threads[i-1]);
    pthread_cond_destroy(&pool->done);
    pthread_cond_destroy(&pool->ready);
    pthread_mutex_destroy(&pool->mutex);
    pool->initialized=0;pool->workers=0;
}
static void rove_parallel_pool(RoveParallel *p) {
    RoveParallelPool *pool=&rove_parallel_threads;
    /* Startup fixes the worker profile. A failed allocation is an explicit
     * failure, never a silently reduced worker count. The lazy call permits
     * standalone scheduler tests; the engine initializes this before UCI. */
    if(atomic_load(&p->resource_failed))return;
    if(!rove_parallel_init(p->workers)) {
        atomic_store(&p->resource_failed,1);
        return;
    }
    pthread_mutex_lock(&pool->mutex);
    if(pool->job) {
        fprintf(stderr,"Rove4k: overlapping search-pool sessions\n");
        atomic_store(&p->resource_failed,1);
        pthread_mutex_unlock(&pool->mutex);
        return;
    }
    pool->job=p;pool->finished=0;pool->epoch++;
    pthread_cond_broadcast(&pool->ready);
    pthread_mutex_unlock(&pool->mutex);
    RoveParallelWorker caller={p,0};
    rove_parallel_worker(&caller);
    pthread_mutex_lock(&pool->mutex);
    while(pool->finished<pool->workers-1)pthread_cond_wait(&pool->done,&pool->mutex);
    /* All helpers have returned from the callback and no longer access p.
     * This completion barrier precedes root/TT/session reuse. Shutdown joins
     * the persistent threads before engine workspace can be freed. */
    pool->job=0;
    pthread_cond_broadcast(&pool->done);
    pthread_mutex_unlock(&pool->mutex);
}

static RoveParallelResult rove_parallel_search(RoveSearch search,void *context,
        const uint32_t *moves,int n,int depth,int alpha,int beta,
        uint32_t priorfirst,uint32_t priorreply,RoveStopped stopped,
        int workers,int mode,uint64_t generation,RoveParallelHistory *history) {
    RoveParallel p={0};
    int leased=0;
    p.search=search;p.stopped=stopped;p.context=context;p.moves=moves;
    p.n=n;p.depth=depth;p.alpha=alpha;p.beta=beta;p.workers=workers;
    p.mode=mode;p.generation=generation;p.bestalpha=alpha;p.bestgroup=0;
    p.groups=mode==2?(workers+3)/4:1;
    p.result.mode=mode;p.result.groups=p.groups;
    if(workers<1 || workers>512 || n<1 || alpha>=beta || stopped(context))return p.result;
    if(n>256) {
        fprintf(stderr,"Rove4k: root move workspace exceeds fixed capacity\n");
        return p.result;
    }
    uint64_t start=rove_parallel_clock(),proposal_ns=0;
    int mutex_error=pthread_mutex_init(&p.mutex,0);
    if(mutex_error) {
        fprintf(stderr,"Rove4k: root result mutex allocation failed (%d)\n",mutex_error);
        return p.result;
    }
    if(!rove_parallel_init(workers))goto done;
    RoveParallelPool *pool=&rove_parallel_threads;
    pthread_mutex_lock(&pool->mutex);
    if(pool->root_busy) {
        fprintf(stderr,"Rove4k: overlapping root sessions\n");
        pthread_mutex_unlock(&pool->mutex);
        goto done;
    }
    pool->root_busy=1;leased=1;
    p.completed=pool->completed;
    memset(p.completed,0,(size_t)n*sizeof(*p.completed));
    pthread_mutex_unlock(&pool->mutex);
    if(mode==0) {
        rove_parallel_pool(&p);
        goto done;
    }
    int first=0;
    for(int i=0;i<n;i++)if(moves[i]==priorfirst)first=i;
    RoveTask proposal={moves[first],priorreply,depth,alpha,beta,ROVE_NORMAL,0,generation,p.groups};
    RoveResult r=search(context,&proposal,0);
    proposal_ns=rove_parallel_clock()-start;
    p.result.assigned++;
    rove_parallel_accept(&p,first,proposal,r);
    if(!rove_parallel_valid(&proposal,&r))goto done;
    if(mode==4) {
        /* Instability is measured between completed iterations. Probe cost
         * and available parallel work determine whether extra PALS work is
         * affordable; stable, costly frontiers use locality groups. */
        int unstable=history && history->depth+1==depth &&
            (abs(history->score-r.score)>=32 ||
             (history->reply && r.reply && history->reply!=r.reply));
        p.mode=unstable && proposal_ns*4<history->total_ns+proposal_ns && n>=workers?3:
            workers>=8 && n>=workers && proposal_ns>=50000?2:1;
        p.groups=p.mode==2?(workers+3)/4:1;
        p.result.mode=p.mode;p.result.groups=p.groups;
    }
    if(p.mode==3 && depth>1 && r.bound!=ROVE_UPPER) {
        if(stopped(context))goto done;
        RoveTask select=proposal;select.kind=ROVE_SELECT_REPLY;select.reply=r.reply;
        RoveResult selected=search(context,&select,0);
        if(stopped(context) || !rove_parallel_valid(&select,&selected))goto done;
        uint32_t challenged=selected.reply;
        if(challenged) {
            RoveTask clause={moves[first],challenged,depth,r.score-1,r.score,
                             ROVE_COUNTERREPLY,0,generation,p.groups};
            RoveResult counter=search(context,&clause,0);
            p.result.clauses++;
            if(stopped(context) || !rove_parallel_valid(&clause,&counter) ||
               counter.reply!=challenged)goto done;
            if(rove_parallel_refutes(&clause,&counter,r.score)) {
                RoveTask repair={moves[first],challenged,depth,alpha,beta,
                                 ROVE_REPAIR,0,generation,p.groups};
                RoveResult repaired=search(context,&repair,0);
                p.result.repairs++;
                if(stopped(context) || !rove_parallel_valid(&repair,&repaired))goto done;
                /* A lower repaired score must replace the old alpha too. No
                 * other root work has started, so only this slot is incumbent. */
                p.bestalpha=alpha;p.bestgroup=0;
                memset(&p.completed[first],0,sizeof p.completed[first]);
                rove_parallel_accept(&p,first,repair,repaired);
                if(repaired.bound==ROVE_UPPER)goto done;
                clause.alpha=repaired.score-1;clause.beta=repaired.score;
                counter=search(context,&clause,0);
                p.result.clauses++;
                if(stopped(context) || !rove_parallel_valid(&clause,&counter) ||
                   counter.reply!=challenged ||
                   rove_parallel_refutes(&clause,&counter,repaired.score))goto done;
            }
        }
    }
    rove_parallel_pool(&p);
    p.result.completedall=1;
    p.result.best.score=INT_MIN;
    for(int i=0;i<n;i++) {
        RoveCompleted *c=&p.completed[i];
        if(!c->result.complete) {p.result.completedall=0;continue;}
        if(c->result.score>p.result.best.score ||
           (c->result.score==p.result.best.score &&
            p.result.best.bound==ROVE_UPPER && c->result.bound!=ROVE_UPPER))
            p.result.best=c->result;
    }
    if(p.result.best.score==INT_MIN)p.result.completedall=0;
    if(p.result.best.complete && p.result.best.bound!=ROVE_UPPER &&
       p.result.best.score>=beta)p.result.completedall=1;
    if(p.result.completedall) {
        p.result.best.complete=1;
        p.result.best.bound=p.result.best.score>=beta?ROVE_LOWER:
            p.result.best.score<=alpha?ROVE_UPPER:ROVE_EXACT;
    }
done:
    if(atomic_load(&p.resource_failed))p.result.completedall=0;
    if(!p.result.completedall)p.result.best.complete=0;
    if(history && p.result.completedall) {
        history->first=p.result.best.first;history->reply=p.result.best.reply;
        history->score=p.result.best.score;history->depth=depth;
        history->proposal_ns=mode?proposal_ns:0;
        history->total_ns=rove_parallel_clock()-start;
        history->nodes=p.result.best.nodes;
    }
    if(leased) {
        pthread_mutex_lock(&rove_parallel_threads.mutex);
        rove_parallel_threads.root_busy=0;
        pthread_cond_broadcast(&rove_parallel_threads.done);
        pthread_mutex_unlock(&rove_parallel_threads.mutex);
    }
    pthread_mutex_destroy(&p.mutex);
    return p.result;
}
#endif
