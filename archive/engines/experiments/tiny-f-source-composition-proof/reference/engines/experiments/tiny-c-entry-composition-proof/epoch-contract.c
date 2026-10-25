/* Bounded actual DEV0 epoch ownership witness, not a shipping image.
 * Production text is included unchanged. Call interposition only observes
 * publications/results and schedules the first real worker clock call so
 * the controller necessarily enters a positive-pending production wait.
 * The real clock value, search, worker, go, wait and result bodies remain.
 */
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <time.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>

static int diagnostic_clock_gettime(clockid_t,struct timespec *);
static int diagnostic_cond_wait(pthread_cond_t *,pthread_mutex_t *);
static int diagnostic_cond_broadcast(pthread_cond_t *);
static int diagnostic_printf(const char *,...);
#define clock_gettime diagnostic_clock_gettime
#define pthread_cond_wait diagnostic_cond_wait
#define pthread_cond_broadcast diagnostic_cond_broadcast
#define printf diagnostic_printf
#define main production_main
#include PRODUCTION_SOURCE
#undef main
#undef printf
#undef pthread_cond_broadcast
#undef pthread_cond_wait
#undef clock_gettime

static pthread_t controller,created_threads[WORKERS];
static pthread_mutex_t diagnostic_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t diagnostic_condition=PTHREAD_COND_INITIALIZER;
static unsigned sequence,gate_mask;
static int gate_closed,gate_id,created_count,joined_count,result_count,violations;

static void event(const char *name,const char *format,...){
    /* Caller holds diagnostic_mutex. */
    fprintf(stderr,"{\"seq\":%u,\"event\":\"%s\"",++sequence,name);
    va_list ap;va_start(ap,format);vfprintf(stderr,format,ap);va_end(ap);
    fputs("}\n",stderr);fflush(stderr);
}
static void violation(const char *message){
    ++violations;event("violation",",\"message\":\"%s\"",message);
}
static int worker_index(void){
    for(int i=0;i<created_count;i++)if(pthread_equal(pthread_self(),created_threads[i]))return i;
    return -1;
}
static void board_fields(void){
    fputs(",\"board\":[",stderr);
    for(int i=0;i<64;i++)fprintf(stderr,"%s%d",i?",":"",position.b[(i/8)*16+i%8]);
    fprintf(stderr,"],\"side\":%d,\"castles\":%d,\"ep\":%d,\"half\":%d,\"hash\":\"%016llx\",\"path\":\"%016llx\",\"game_length\":%d,\"game_keys\":[",
        position.s,position.c,position.e,position.half,(unsigned long long)position.h,(unsigned long long)position.r,game_length);
    for(int i=0;i<game_length;i++)fprintf(stderr,"%s\"%016llx\"",i?",":"",(unsigned long long)game_keys[i]);
    fputs("]",stderr);
}
static void snapshot(const char *name,int inspect_workers){
    /* Lock order is always production mutex then diagnostic mutex.
     * Worker clock hooks take only diagnostic_mutex, never production mutex. */
    pthread_mutex_lock(&mutex);pthread_mutex_lock(&diagnostic_mutex);
    if(inspect_workers&&pending)violation("worker-read-requested-before-pending-zero");
    fprintf(stderr,"{\"seq\":%u,\"event\":\"%s\",\"epoch\":%u,\"pending\":%d,\"stopped\":%d,\"results\":%d",
        ++sequence,name,epoch,pending,atomic_load(&stopped),result_count);
    board_fields();
    if(inspect_workers&&!pending){
        fputs(",\"workers\":[",stderr);
        for(int i=0;i<WORKERS;i++){
            Worker *w=workers+i;
            fprintf(stderr,"%s{\"id\":%d,\"nodes\":%llu,\"depth\":%d,\"score\":%d,\"best\":%u,\"length\":%d,\"history_matches\":%s}",
                i?",":"",w->id,(unsigned long long)w->nodes,w->depth,w->score,w->best,w->length,
                w->length==game_length&&!memcmp(w->keys,game_keys,game_length*sizeof *game_keys)?"true":"false");
        }
        fputs("]",stderr);
    }
    fputs("}\n",stderr);fflush(stderr);
    pthread_mutex_unlock(&diagnostic_mutex);pthread_mutex_unlock(&mutex);
}
static int diagnostic_clock_gettime(clockid_t clock_id,struct timespec *time_value){
    if(!pthread_equal(pthread_self(),controller)){
        pthread_mutex_lock(&diagnostic_mutex);
        if(gate_closed){
            int index=worker_index();
            if(index<0)violation("unowned-worker-clock");
            else{
                gate_mask|=1u<<index;
                event("worker_claim_clock",",\"gate\":%d,\"worker\":%d,\"thread\":%llu,\"held_mask\":%u",gate_id,index,(unsigned long long)pthread_self(),gate_mask);
            }
            pthread_cond_broadcast(&diagnostic_condition);
            while(gate_closed)pthread_cond_wait(&diagnostic_condition,&diagnostic_mutex);
        }
        pthread_mutex_unlock(&diagnostic_mutex);
    }
    return clock_gettime(clock_id,time_value);
}
static int diagnostic_cond_wait(pthread_cond_t *condition,pthread_mutex_t *lock){
    if(pthread_equal(pthread_self(),controller)&&condition==&finished&&lock==&mutex){
        pthread_mutex_lock(&diagnostic_mutex);
        event("production_wait_condition",",\"epoch\":%u,\"pending\":%d,\"stopped\":%d,\"gate\":%d,\"held_mask\":%u,\"gate_closed\":%s",
            epoch,pending,atomic_load(&stopped),gate_id,gate_mask,gate_closed?"true":"false");
        if(gate_closed){
            if(!gate_mask)violation("wait-released-unobserved-gate");
            gate_closed=0;pthread_cond_broadcast(&diagnostic_condition);
        }
        pthread_mutex_unlock(&diagnostic_mutex);
    }
    return pthread_cond_wait(condition,lock);
}
static int diagnostic_cond_broadcast(pthread_cond_t *condition){
    if(condition==&command){
        /* Every production command publication holds production mutex. */
        pthread_mutex_lock(&diagnostic_mutex);
        event(quitting?"shutdown_publication":"go_publication",
            ",\"epoch\":%u,\"pending\":%d,\"stopped\":%d,\"quitting\":%d,\"results\":%d,\"side\":%d,\"game_length\":%d",
            epoch,pending,atomic_load(&stopped),quitting,result_count,position.s,game_length);
        pthread_mutex_unlock(&diagnostic_mutex);
    }
    return pthread_cond_broadcast(condition);
}
static int diagnostic_printf(const char *format,...){
    va_list ap;va_start(ap,format);
    if(!strcmp(format,"bestmove %s\n")){
        va_list copy;va_copy(copy,ap);const char *move=va_arg(copy,const char *);va_end(copy);
        /* Actual result() is called only by the final completing worker,
         * while holding production mutex and after pending reaches zero. */
        pthread_mutex_lock(&diagnostic_mutex);
        if(pending)violation("actual-result-before-pending-zero");
        ++result_count;
        fprintf(stderr,"{\"seq\":%u,\"event\":\"actual_result\",\"epoch\":%u,\"pending\":%d,\"stopped\":%d,\"ordinal\":%d,\"move\":\"%s\"",
            ++sequence,epoch,pending,atomic_load(&stopped),result_count,move);
        board_fields();fputs("}\n",stderr);fflush(stderr);
        pthread_mutex_unlock(&diagnostic_mutex);
    }
    int rc=vfprintf(stdout,format,ap);va_end(ap);return rc;
}
static void arm(int id){
    pthread_mutex_lock(&diagnostic_mutex);
    if(gate_closed)violation("prior-gate-still-closed");
    gate_id=id;gate_mask=0;gate_closed=1;
    event("gate_armed",",\"gate\":%d",id);
    pthread_mutex_unlock(&diagnostic_mutex);
}
static int observed(int id){
    struct timespec end;clock_gettime(CLOCK_REALTIME,&end);end.tv_sec+=2;
    pthread_mutex_lock(&diagnostic_mutex);
    while(!gate_mask){
        int rc=pthread_cond_timedwait(&diagnostic_condition,&diagnostic_mutex,&end);
        if(rc){violation(rc==ETIMEDOUT?"worker-clock-observation-timeout":"diagnostic-condwait-error");break;}
    }
    int okay=gate_mask!=0&&gate_id==id&&gate_closed;
    event("controller_observed_claim",",\"gate\":%d,\"held_mask\":%u,\"gate_closed\":%s,\"okay\":%s",id,gate_mask,gate_closed?"true":"false",okay?"true":"false");
    if(!okay){gate_closed=0;pthread_cond_broadcast(&diagnostic_condition);}
    pthread_mutex_unlock(&diagnostic_mutex);
    return okay;
}
int main(void){
    controller=pthread_self();
    table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;
    clear();start(&position);game_keys[0]=position.h;game_length=1;
    pthread_mutex_lock(&diagnostic_mutex);
    event("fixture",",\"source_sha256\":\"15999279c5bd4690db7129bda032c6b5962acbd814236719cda40755ae31794b\",\"DEV\":%d,\"workers\":%d,\"tt_bits\":%d",DEV,WORKERS,TT_BITS);
    pthread_mutex_unlock(&diagnostic_mutex);
    int status=0;
    for(;created_count<WORKERS;created_count++){
        workers[created_count].id=created_count;
        if(pthread_create(created_threads+created_count,0,work,workers+created_count)){status=2;goto shutdown;}
    }
    wait();snapshot("startup_wait_return",1);
    arm(1);
    {char text[]=" wtime 300000 btime 300000";go(text);}
    if(!observed(1)){status=1;goto drain;}
    snapshot("before_go_replacement",0);
    {char text[]=" wtime 0 btime 0";go(text);}
    wait();snapshot("replacement_wait_return",1);
    arm(3);
    {char text[]=" wtime 300000 btime 300000";go(text);}
    if(!observed(3)){status=1;goto drain;}
    snapshot("before_position_wait",0);
    wait();snapshot("position_wait_return",1);
    {char text[]="startpos moves e2e4";set_position(text);}
    snapshot("position_reused_after_wait",0);
    {char text[]=" wtime 0 btime 0";go(text);}
    wait();snapshot("black_wait_return",1);
drain:
    wait();
shutdown:
    pthread_mutex_lock(&diagnostic_mutex);gate_closed=0;pthread_cond_broadcast(&diagnostic_condition);pthread_mutex_unlock(&diagnostic_mutex);
    pthread_mutex_lock(&mutex);quitting=1;diagnostic_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
    for(int i=0;i<created_count;i++){
        int rc=pthread_join(created_threads[i],0);
        pthread_mutex_lock(&diagnostic_mutex);
        if(!rc)++joined_count;else{status=2;violation("real-join-failed");}
        event("join_return",",\"worker\":%d,\"returncode\":%d,\"thread\":%llu",i,rc,(unsigned long long)created_threads[i]);
        pthread_mutex_unlock(&diagnostic_mutex);
    }
    /* This witness makes no safety claim for real pthread_join failure. */
    if(joined_count==created_count){free(table);table=0;}
    pthread_mutex_lock(&diagnostic_mutex);
    event("fixture_return",",\"status\":%d,\"results\":%d,\"created\":%d,\"joined\":%d,\"violations\":%d,\"table_freed\":%s",
        status,result_count,created_count,joined_count,violations,table?"false":"true");
    pthread_mutex_unlock(&diagnostic_mutex);
    return status?status:violations?1:0;
}
