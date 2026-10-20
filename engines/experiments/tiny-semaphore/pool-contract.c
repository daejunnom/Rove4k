/* Test-only interposition. The frozen runtime body is included unchanged;
 * no semaphore, gate, or trace field is added to the shipped Worker type. */
#define _GNU_SOURCE
#include <pthread.h>
#include <semaphore.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/syscall.h>
#include "tiny.h"
#include BOARD_SOURCE
#include SEARCH_SOURCE

static int contract_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
static int contract_join(pthread_t,void **);
static int contract_init(sem_t *,int,unsigned);
static int contract_take(sem_t *);
static int contract_post(sem_t *);
static int contract_destroy(sem_t *);
static void *contract_allocate(size_t,size_t);
static int contract_flush(FILE *);
static void *contract_copy(void *,const void *,size_t);

#define main engine_main
#define pthread_create contract_create
#define pthread_join contract_join
#define sem_init contract_init
#define sem_wait contract_take
#define sem_post contract_post
#define sem_destroy contract_destroy
#define calloc contract_allocate
#define fflush contract_flush
#define memcpy contract_copy
#include RUNTIME_SOURCE
#undef main
#undef pthread_create
#undef pthread_join
#undef sem_init
#undef sem_wait
#undef sem_post
#undef sem_destroy
#undef calloc
#undef fflush
#undef memcpy

static char contract_mode[32]="normal";
static int contract_index,contract_control=-1,contract_creates;
static pthread_t contract_main,contract_ids[WORKERS];
static atomic_int contract_triggered,contract_interrupted[WORKERS+2],contract_generation,contract_late_seen;
static pthread_mutex_t contract_trace_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t contract_gate_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t contract_gate=PTHREAD_COND_INITIALIZER;
static int contract_late_released;
static unsigned long long contract_sequence;

static int mode(const char *name){return !strcmp(contract_mode,name);}
static int is_main(void){return pthread_equal(pthread_self(),contract_main);}
static int slot(const sem_t *sem){return (int)(sem-signals);}
static int once(void){return !atomic_exchange(&contract_triggered,1);}
static void event(const char *name,int index,long long value,uint64_t hash){
    pthread_mutex_lock(&contract_trace_mutex);
    fprintf(stderr,"{\"seq\":%llu,\"tid\":%ld,\"event\":\"%s\",\"index\":%d,\"value\":%lld,\"generation\":%d,\"hash\":\"%016llx\"}\n",
        ++contract_sequence,(long)syscall(SYS_gettid),name,index,value,
        atomic_load(&contract_generation),(unsigned long long)hash);
    fflush(stderr);pthread_mutex_unlock(&contract_trace_mutex);
}
static void hold(const char *name,int index){
    event(name,index,atomic_load(&pending),0);
    char byte;ssize_t n;
    do n=read(contract_control,&byte,1);while(n<0&&errno==EINTR);
    if(n!=1){event("control_error",index,n,0);_Exit(90);}
    event("released",index,atomic_load(&pending),0);
}
static int contract_init(sem_t *sem,int shared,unsigned value){
    int index=slot(sem);
    if(mode("init-fail")&&index==contract_index){event("init_fail",index,value,0);errno=ENOSPC;return -1;}
    int code=sem_init(sem,shared,value);event(code?"init_error":"init",index,value,0);return code;
}
static int contract_create(pthread_t *thread,const pthread_attr_t *attributes,void *(*start)(void *),void *argument){
    int index=contract_creates++;
    if(mode("create-fail")&&index==contract_index){event("create_fail",index,EAGAIN,0);return EAGAIN;}
    int code=pthread_create(thread,attributes,start,argument);
    if(!code)contract_ids[index]=*thread;
    event(code?"create_error":"create",index,code,0);return code;
}
static int contract_join(pthread_t thread,void **result){
    int index=-1;for(int i=0;i<contract_creates&&i<WORKERS;i++)if(pthread_equal(thread,contract_ids[i])){index=i;break;}
    if(mode("join-fail")&&index==contract_index){event("join_fail",index,EINVAL,0);return EINVAL;}
    int code=pthread_join(thread,result);event(code?"join_error":"join",index,code,0);return code;
}
static int contract_take(sem_t *sem){
    int index=slot(sem);
    if(mode("eintr-each")&&!atomic_exchange(contract_interrupted+index,1)){
        event("wait_eintr",index,atomic_load(&pending),0);errno=EINTR;return -1;
    }
    if(mode("wait-fail")&&index==contract_index&&once()){
        event("wait_fail",index,atomic_load(&pending),0);errno=EINVAL;return -1;
    }
    if(mode("late-wait")&&index==WORKERS-1&&!atomic_exchange(&contract_late_seen,1)){
        event("wait_gate",index,atomic_load(&pending),0);
        pthread_mutex_lock(&contract_gate_mutex);
        while(!contract_late_released)pthread_cond_wait(&contract_gate,&contract_gate_mutex);
        pthread_mutex_unlock(&contract_gate_mutex);
    }
    event("wait_enter",index,atomic_load(&pending),0);
    int code=sem_wait(sem);
    event(code?"wait_error":"wait_return",index,atomic_load(&pending),0);
    if(!code&&index<WORKERS){
        if(quitting)event("quit_wake",index,atomic_load(&pending),0);
        else{
            event("job",index,atomic_load(&pending),0);
            if(mode("hold-worker")&&index==WORKERS-1&&once())hold("hold_worker",index);
        }
    }
    return code;
}
static int contract_post(sem_t *sem){
    int index=slot(sem),main=is_main();
    if(mode("post-fail")&&index==contract_index&&(index!=WORKERS||!main)&&once()){
        event("post_fail",index,atomic_load(&pending),0);errno=EINVAL;return -1;
    }
    if(mode("hold-done")&&index==WORKERS&&!main&&once())hold("hold_done",index);
    if(index==0&&main&&!quitting){atomic_fetch_add(&contract_generation,1);event("publish",index,atomic_load(&pending),position.h);}
    int code=sem_post(sem);event(code?"post_error":"post",index,atomic_load(&pending),0);
    if(!code&&index==WORKERS+1)event("worker_ready",index,atomic_load(&pending),0);
    if(!code&&mode("late-wait")&&index==WORKERS-1&&main){
        pthread_mutex_lock(&contract_gate_mutex);contract_late_released=1;
        pthread_cond_broadcast(&contract_gate);pthread_mutex_unlock(&contract_gate_mutex);
    }
    return code;
}
static int contract_destroy(sem_t *sem){
    int index=slot(sem),code=sem_destroy(sem);event(code?"destroy_error":"destroy",index,code,0);return code;
}
static void *contract_allocate(size_t count,size_t size){
    if(mode("calloc-fail")){event("calloc_fail",0,0,0);errno=ENOMEM;return NULL;}
    void *result=calloc(count,size);event("calloc",0,(long long)(count*size),0);return result;
}
static int contract_flush(FILE *stream){
    if(stream==stdout&&!is_main()&&mode("hold-output")&&once())hold("hold_output",WORKERS);
    int code=fflush(stream);
    if(stream==stdout&&!is_main())event("output_flushed",WORKERS,code,0);
    return code;
}
static void *contract_copy(void *destination,const void *source,size_t size){
    void *result=memcpy(destination,source,size);
    if(destination==game_keys)event("position_commit",0,game_length,position.h);
    return result;
}
int main(int argc,char **argv){
    contract_main=pthread_self();
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--mode")&&i+1<argc){strncpy(contract_mode,argv[++i],sizeof contract_mode-1);}
        else if(!strcmp(argv[i],"--index")&&i+1<argc)contract_index=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--control-fd")&&i+1<argc)contract_control=atoi(argv[++i]);
        else return 90;
    }
    event("fixture_start",-1,WORKERS,0);
    int code=engine_main();event("exit",-1,code,0);return code;
}
