#define _POSIX_C_SOURCE 200809L
#define ROVE_WORKERS 4
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <assert.h>
#include "fixed_loose.h"

typedef struct {
    pthread_barrier_t barrier;
    _Atomic int active,peak,calls,stop;
    int invalid_zero;
} Context;
static int stopped(void *arg) {return atomic_load(&((Context *)arg)->stop);}
static RoveResult callback(void *arg,const RoveTask *task,unsigned id) {
    Context *c=arg;
    assert(task->first==0&&task->group==0&&task->groups==1);
    assert(task->generation==42&&task->depth==4);
    int live=atomic_fetch_add(&c->active,1)+1,peak=atomic_load(&c->peak);
    while(peak<live&&!atomic_compare_exchange_weak(&c->peak,&peak,live)){}
    atomic_fetch_add(&c->calls,1);
    int status=pthread_barrier_wait(&c->barrier);
    assert(status==0||status==PTHREAD_BARRIER_SERIAL_THREAD);
    RoveResult r={10+(int)id,ROVE_EXACT,1,id+1,0,1};
    if(!id&&c->invalid_zero==1)r.complete=0;
    if(!id&&c->invalid_zero==2)r.bound=ROVE_LOWER; /* cannot prove beta=100 */
    atomic_fetch_sub(&c->active,1);
    return r;
}
static RoveParallelResult invoke(Context *c) {
    RoveParallelHistory history={0};uint32_t moves[2]={7,9};
    return rove_parallel_search(callback,c,moves,2,4,-100,100,7,9,stopped,4,0,42,&history);
}
int main(void) {
    for(int cycle=0;cycle<2;cycle++) {
        assert(!rove_parallel_init(3));
        assert(rove_parallel_init(4));
        assert(rove_parallel_init(4));
        Context c={0};assert(!pthread_barrier_init(&c.barrier,0,4));
        for(int invalid=0;invalid<3;invalid++) {
            c.invalid_zero=invalid;
            RoveParallelResult r=invoke(&c);
            assert(r.completedall&&r.best.complete&&r.best.bound==ROVE_EXACT);
            assert(r.best.score==(invalid?11:10)&&r.best.first==(invalid?2:1));
            assert(r.groups==1&&r.mode==0&&r.assigned==4);
            assert(atomic_load(&c.active)==0&&atomic_load(&c.peak)==4);
        }
        assert(atomic_load(&c.calls)==12);
        atomic_store(&c.stop,1);
        RoveParallelResult r=invoke(&c);
        assert(!r.completedall&&!r.best.complete&&atomic_load(&c.calls)==12);
        rove_parallel_shutdown();
        assert(!rove_loose.initialized&&atomic_load(&c.active)==0);
        assert(!pthread_barrier_destroy(&c.barrier));
    }
    puts("fixed loose startup, overlap, completed precedence, cancellation and join passed");
}
