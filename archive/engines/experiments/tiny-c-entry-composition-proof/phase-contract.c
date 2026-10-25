/* Bounded startup-phase diagnostic. Compile against the unchanged candidate:
 * cc -std=c11 -Os -pthread -DDEV=0 -DWORKERS=2 -DTT_BITS=18 \
 *   '-DPRODUCTION_SOURCE="/absolute/candidate/engine.c"' phase-contract.c -o phase-contract
 * The runner supplies uci/isready/quit only. No time-based scheduling gates.
 * All production pending/quitting observations occur with its mutex held.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <limits.h>
#include <errno.h>
#include <stdarg.h>

#ifndef PRODUCTION_SOURCE
#error PRODUCTION_SOURCE must name the unchanged candidate translation unit
#endif

static int diagnostic_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
static int diagnostic_join(pthread_t,void **);
static int diagnostic_mutex_lock(pthread_mutex_t *);
static int diagnostic_mutex_unlock(pthread_mutex_t *);
static int diagnostic_cond_wait(pthread_cond_t *,pthread_mutex_t *);
static int diagnostic_cond_broadcast(pthread_cond_t *);
static int diagnostic_getchar(void);
static void diagnostic_free(void *);

#define main production_main
#define pthread_create diagnostic_create
#define pthread_join diagnostic_join
#define pthread_mutex_lock diagnostic_mutex_lock
#define pthread_mutex_unlock diagnostic_mutex_unlock
#define pthread_cond_wait diagnostic_cond_wait
#define pthread_cond_broadcast diagnostic_cond_broadcast
#define getchar diagnostic_getchar
#define free diagnostic_free
#include PRODUCTION_SOURCE
#undef main
#undef pthread_create
#undef pthread_join
#undef pthread_mutex_lock
#undef pthread_mutex_unlock
#undef pthread_cond_wait
#undef pthread_cond_broadcast
#undef getchar
#undef free

#if WORKERS != 2 || DEV != 0
#error This diagnostic has exactly two production workers and shipping commands
#endif

enum diagnostic_mode {
    SUCCESS_EARLY,SUCCESS_LATE,FAIL_0,FAIL_1_EARLY,FAIL_1_LATE
};
enum { DIAGNOSTIC_WORKERS=2,TRACE_LIMIT=256 };
static const char *const mode_names[]={
    "success-early","success-late","fail-0","fail-1-early","fail-1-late"
};
static pthread_mutex_t diagnostic_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t diagnostic_changed=PTHREAD_COND_INITIALIZER;
static _Thread_local int diagnostic_index=-1;
static struct {
    enum diagnostic_mode mode;
    unsigned sequence;
    int attempts,created,joined,entered,exited,arrivals,input_calls,tt_frees;
    int startup_expected,startup_active,startup_entered,startup_returned;
    int gate_open[DIAGNOSTIC_WORKERS];
    int arrived[DIAGNOSTIC_WORKERS],has_joined[DIAGNOSTIC_WORKERS];
    int first_lock[DIAGNOSTIC_WORKERS],violations;
    pthread_t identities[DIAGNOSTIC_WORKERS];
} diagnostic;
static struct diagnostic_start {
    void *(*entry)(void *);
    void *argument;
    int index;
} diagnostic_starts[DIAGNOSTIC_WORKERS];

static void diagnostic_lock(void){
    if(pthread_mutex_lock(&diagnostic_mutex))_Exit(90);
}
static void diagnostic_unlock(void){
    if(pthread_mutex_unlock(&diagnostic_mutex))_Exit(90);
}
static void diagnostic_notify(void){
    if(pthread_cond_broadcast(&diagnostic_changed))_Exit(90);
}
static void diagnostic_wait(void){
    if(pthread_cond_wait(&diagnostic_changed,&diagnostic_mutex))_Exit(90);
}
/* A pthread_t is opaque: retain its complete implementation representation.
 * The runner compares these strings and pthread_equal is used internally. */
static void diagnostic_thread_text(pthread_t thread,char *out){
    static const char hex[]="0123456789abcdef";
    const unsigned char *p=(const unsigned char *)&thread;
    for(size_t i=0;i<sizeof thread;i++){
        out[2*i]=hex[p[i]>>4];out[2*i+1]=hex[p[i]&15];
    }
    out[2*sizeof thread]=0;
}
/* diagnostic_mutex serializes complete JSON lines and their sequence. */
static void diagnostic_event(const char *event,int index,const char *fields,...){
    char thread[2*sizeof(pthread_t)+1];
    diagnostic_thread_text(pthread_self(),thread);
    if(diagnostic.sequence>=TRACE_LIMIT)_Exit(90);
    fprintf(stderr,"{\"event\":\"%s\",\"seq\":%u,\"actor\":\"%s\",\"index\":%d,\"thread\":\"%s\"",
        event,++diagnostic.sequence,diagnostic_index<0?"main":"worker",index,thread);
    if(fields&&*fields){
        va_list args;va_start(args,fields);vfprintf(stderr,fields,args);va_end(args);
    }
    fputs("}\n",stderr);fflush(stderr);
}
static void diagnostic_violation(const char *reason,int index){
    diagnostic.violations++;
    diagnostic_event("contract_violation",index,",\"reason\":\"%s\"",reason);
}
static void diagnostic_release(int index,const char *reason){
    if(diagnostic.gate_open[index])return;
    diagnostic.gate_open[index]=1;
    diagnostic_event("worker_gate_release",index,",\"reason\":\"%s\"",reason);
    diagnostic_notify();
}
static void *diagnostic_trampoline(void *argument){
    struct diagnostic_start *s=argument;
    diagnostic_index=s->index;
    diagnostic_lock();
    if(!diagnostic.gate_open[s->index])
        diagnostic_event("worker_gate_wait",s->index,"");
    while(!diagnostic.gate_open[s->index])diagnostic_wait();
    diagnostic.entered++;
    diagnostic_event("worker_entry",s->index,"");
    diagnostic_unlock();
    void *result=s->entry(s->argument);
    diagnostic_lock();
    diagnostic.exited++;
    diagnostic_event("worker_exit",s->index,"");
    diagnostic_unlock();
    return result;
}
static int diagnostic_create(pthread_t *thread,const pthread_attr_t *attr,
        void *(*entry)(void *),void *argument){
    diagnostic_lock();
    int index=diagnostic.attempts++;
    diagnostic_event("create_attempt",index,"");
    if(index<0||index>=DIAGNOSTIC_WORKERS){
        diagnostic_violation("unexpected-create-index",index);
        diagnostic_unlock();return EAGAIN;
    }
    int fail=(diagnostic.mode==FAIL_0&&index==0)||
        ((diagnostic.mode==FAIL_1_EARLY||diagnostic.mode==FAIL_1_LATE)&&index==1);
    if(fail){
        if(diagnostic.mode==FAIL_1_EARLY)
            while(!diagnostic.arrived[0])diagnostic_wait();
        diagnostic_event("create_return",index,
            ",\"rc\":%d,\"created\":%d,\"target_thread\":null",EAGAIN,diagnostic.created);
        diagnostic_unlock();return EAGAIN;
    }
    diagnostic_starts[index]=(struct diagnostic_start){entry,argument,index};
    diagnostic_unlock();
    int rc=pthread_create(thread,attr,diagnostic_trampoline,diagnostic_starts+index);
    diagnostic_lock();
    if(!rc){
        char target[2*sizeof(pthread_t)+1];
        diagnostic.identities[index]=*thread;diagnostic.created++;
        diagnostic_thread_text(*thread,target);
        diagnostic_event("create_return",index,
            ",\"rc\":0,\"created\":%d,\"target_thread\":\"%s\"",diagnostic.created,target);
        if(index==DIAGNOSTIC_WORKERS-1){
            if(diagnostic.mode==SUCCESS_EARLY)
                while(diagnostic.arrivals!=DIAGNOSTIC_WORKERS)diagnostic_wait();
            diagnostic.startup_expected=1;
        }
    }else diagnostic_event("create_return",index,
        ",\"rc\":%d,\"created\":%d,\"target_thread\":null",rc,diagnostic.created);
    diagnostic_unlock();return rc;
}
static int diagnostic_join(pthread_t thread,void **result){
    char target[2*sizeof(pthread_t)+1];
    diagnostic_thread_text(thread,target);
    diagnostic_lock();
    int index=-1;
    for(int i=0;i<diagnostic.created;i++)
        if(!diagnostic.has_joined[i]&&pthread_equal(thread,diagnostic.identities[i]))index=i;
    if(index<0)diagnostic_violation("join-without-successful-create",index);
    diagnostic_event("join_enter",index,",\"target_thread\":\"%s\"",target);
    diagnostic_unlock();
    int rc=pthread_join(thread,result);
    diagnostic_lock();
    if(!rc){
        if(index>=0&&diagnostic.has_joined[index])
            diagnostic_violation("duplicate-successful-join",index);
        if(index>=0)diagnostic.has_joined[index]=1;
        diagnostic.joined++;
    }
    diagnostic_event("join_return",index,
        ",\"rc\":%d,\"joined\":%d,\"target_thread\":\"%s\"",rc,diagnostic.joined,target);
    diagnostic_unlock();return rc;
}
static int diagnostic_mutex_lock(pthread_mutex_t *m){
    int rc=pthread_mutex_lock(m);
    if(rc||m!=&mutex)return rc;
    diagnostic_lock();
    if(diagnostic_index>=0){
        if(!diagnostic.first_lock[diagnostic_index]){
            diagnostic.first_lock[diagnostic_index]=1;
            diagnostic_event("worker_mutex_acquired",diagnostic_index,
                ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d",
                pending,quitting,atomic_load(&stopped));
        }
    }else if(diagnostic.startup_expected&&!diagnostic.startup_entered){
        diagnostic.startup_active=1;diagnostic.startup_entered++;
        diagnostic_event("main_startup_wait_enter",-1,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d",
            pending,quitting,atomic_load(&stopped));
    }
    diagnostic_unlock();return rc;
}
static int diagnostic_mutex_unlock(pthread_mutex_t *m){
    int startup=0,p=0,q=0,s=0;
    if(m==&mutex&&diagnostic_index<0){
        diagnostic_lock();startup=diagnostic.startup_active;diagnostic_unlock();
        if(startup){p=pending;q=quitting;s=atomic_load(&stopped);}
    }
    int rc=pthread_mutex_unlock(m);
    if(startup){
        diagnostic_lock();
        diagnostic.startup_active=0;diagnostic.startup_returned++;
        diagnostic_event("main_startup_wait_return",-1,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d,\"rc\":%d",p,q,s,rc);
        diagnostic_unlock();
    }
    return rc;
}
static int diagnostic_cond_wait(pthread_cond_t *c,pthread_mutex_t *m){
    int startup=0,worker_command=0;
    if(m==&mutex){
        diagnostic_lock();
        startup=diagnostic_index<0&&c==&finished&&diagnostic.startup_active;
        worker_command=diagnostic_index>=0&&c==&command;
        if(startup){
            diagnostic_event("main_finished_wait_enter",-1,
                ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d",
                pending,quitting,atomic_load(&stopped));
            if(diagnostic.mode==SUCCESS_LATE)
                diagnostic_release(1,"main-about-to-real-finished-wait");
        }else if(worker_command)diagnostic_event("worker_command_wait_enter",diagnostic_index,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d",
            pending,quitting,atomic_load(&stopped));
        diagnostic_unlock();
    }
    int rc=pthread_cond_wait(c,m);
    if(startup||worker_command){
        diagnostic_lock();
        diagnostic_event(startup?"main_finished_wait_return":"worker_command_wait_return",
            diagnostic_index,",\"pending\":%d,\"quitting\":%d,\"stopped\":%d,\"rc\":%d",
            pending,quitting,atomic_load(&stopped),rc);
        diagnostic_unlock();
    }
    return rc;
}
static int diagnostic_cond_broadcast(pthread_cond_t *c){
    int rc=pthread_cond_broadcast(c);
    if(c!=&finished&&c!=&command)return rc;
    /* Both candidate call sites hold the production mutex throughout. */
    diagnostic_lock();
    if(c==&finished&&diagnostic_index>=0&&!diagnostic.arrived[diagnostic_index]){
        diagnostic.arrived[diagnostic_index]=1;diagnostic.arrivals++;
        diagnostic_event("worker_arrival",diagnostic_index,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d,\"rc\":%d",
            pending,quitting,atomic_load(&stopped),rc);
        diagnostic_notify();
    }else if(c==&command&&diagnostic_index<0&&quitting){
        diagnostic_event("shutdown_broadcast",-1,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d,\"rc\":%d",
            pending,quitting,atomic_load(&stopped),rc);
        if(diagnostic.mode==FAIL_1_LATE)
            diagnostic_release(0,"after-real-shutdown-command-broadcast");
    }
    diagnostic_unlock();return rc;
}
static int diagnostic_getchar(void){
    diagnostic_lock();int first=diagnostic.input_calls++==0;diagnostic_unlock();
    if(first){
        if(pthread_mutex_lock(&mutex))_Exit(90);
        diagnostic_lock();
        diagnostic_event("first_input",-1,
            ",\"pending\":%d,\"quitting\":%d,\"stopped\":%d",
            pending,quitting,atomic_load(&stopped));
        diagnostic_unlock();
        if(pthread_mutex_unlock(&mutex))_Exit(90);
    }
    return getchar();
}
static void diagnostic_free(void *p){
    int is_table=p==(void *)table;
    free(p);
    if(is_table){
        diagnostic_lock();diagnostic.tt_frees++;
        if(diagnostic.joined!=diagnostic.created||diagnostic.exited!=diagnostic.created)
            diagnostic_violation("tt-free-before-successful-joins-and-exits",-1);
        diagnostic_event("tt_free",-1,
            ",\"created\":%d,\"joined\":%d,\"entered\":%d,\"exited\":%d",
            diagnostic.created,diagnostic.joined,diagnostic.entered,diagnostic.exited);
        diagnostic_unlock();
    }
}
int main(int argc,char **argv){
    int mode=-1;
    if(argc==3&&!strcmp(argv[1],"--mode"))
        for(int i=0;i<5;i++)if(!strcmp(argv[2],mode_names[i]))mode=i;
    if(mode<0){
        fputs("{\"event\":\"usage_error\",\"usage\":\"--mode success-early|success-late|fail-0|fail-1-early|fail-1-late\"}\n",stderr);
        return 64;
    }
    diagnostic.mode=(enum diagnostic_mode)mode;
    for(int i=0;i<DIAGNOSTIC_WORKERS;i++)diagnostic.gate_open[i]=1;
    if(mode==SUCCESS_LATE)diagnostic.gate_open[1]=0;
    if(mode==FAIL_1_LATE)diagnostic.gate_open[0]=0;
    diagnostic_lock();
    diagnostic_event("mode",-1,
        ",\"mode\":\"%s\",\"source_sha256\":\"15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b\"",
        mode_names[mode]);
    diagnostic_unlock();
    int status=production_main();
    diagnostic_lock();
    diagnostic_event("production_return",-1,
        ",\"status\":%d,\"created\":%d,\"joined\":%d,\"entered\":%d,\"exited\":%d,\"arrivals\":%d,\"input_calls\":%d,\"tt_frees\":%d,\"startup_entered\":%d,\"startup_returned\":%d,\"violations\":%d",
        status,diagnostic.created,diagnostic.joined,diagnostic.entered,diagnostic.exited,
        diagnostic.arrivals,diagnostic.input_calls,diagnostic.tt_frees,
        diagnostic.startup_entered,diagnostic.startup_returned,diagnostic.violations);
    diagnostic_unlock();return status;
}
