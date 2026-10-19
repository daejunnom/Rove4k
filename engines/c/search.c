#include "rove.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include "parallel.h"
#if ROVE_VARIANT == 3
#include <immintrin.h>
#endif
#if ROVE_VARIANT == 5 || ROVE_MODEL
#include "model.h"
#endif

TTEntry *rove_tt;
_Atomic uint64_t rove_see_calls,rove_singular_calls,rove_simd_calls,rove_model_calls,rove_mtd_probes;
_Atomic uint64_t rove_mtd_conflicts,rove_mtd_converged;
int parallel_init(void){return rove_parallel_init(ROVE_WORKERS);}
void parallel_shutdown(void){rove_parallel_shutdown();}
void evaluate_init(void){
#if ROVE_VARIANT == 5 || ROVE_MODEL
    rove_model_init();
#endif
}
uint64_t now_ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
void tt_clear(void){if(rove_tt)for(size_t i=0;i<((size_t)1<<ROVE_TT_BITS);i++){atomic_store_explicit(&rove_tt[i].key,0,memory_order_relaxed);atomic_store_explicit(&rove_tt[i].data,0,memory_order_relaxed);
#if ROVE_VARIANT == 6
    atomic_store_explicit(&rove_tt[i].upper_key,0,memory_order_relaxed);atomic_store_explicit(&rove_tt[i].upper_data,0,memory_order_relaxed);
#endif
}}
static int static_score(int score){return score>20000?20000:score< -20000?-20000:score;}
int evaluate_scalar(const Board *p){int s=0;for(int q=0;q<128;q++){if(q&0x88){q+=7;continue;}if(p->b[q])s+=hce_piece(p->b[q],q);}return static_score(p->side*s);}
int evaluate_reference(const Board *p){
#if ROVE_VARIANT == 5 || ROVE_MODEL
    return rove_model_eval_scalar(p->b,p->side);
#else
    return evaluate_scalar(p);
#endif
}
#if ROVE_VARIANT == 3
__attribute__((target("avx2"))) static int evaluate_simd(const Board *p){
    int32_t terms[64];for(int q=0;q<64;q++){int sq=(q/8)*16+q%8;terms[q]=p->b[sq]?hce_piece(p->b[sq],sq):0;}
    __m256i sum=_mm256_setzero_si256();for(int q=0;q<64;q+=8)sum=_mm256_add_epi32(sum,_mm256_loadu_si256((const __m256i *)(terms+q)));
    int32_t lanes[8];_mm256_storeu_si256((__m256i *)lanes,sum);int s=0;for(int i=0;i<8;i++)s+=lanes[i];return static_score(p->side*s);
}
#endif
int evaluate(const Board *p){
#if ROVE_VARIANT == 3 && !ROVE_MODEL
    atomic_fetch_add_explicit(&rove_simd_calls,1,memory_order_relaxed);return evaluate_simd(p);
#elif ROVE_VARIANT == 5 || ROVE_MODEL
    atomic_fetch_add_explicit(&rove_model_calls,1,memory_order_relaxed);
#if ROVE_VARIANT == 3
    atomic_fetch_add_explicit(&rove_simd_calls,1,memory_order_relaxed);
#endif
    return rove_model_eval(p->b,p->side);
#else
    return static_score(p->side*p->hce);
#endif
}
typedef struct {Worker *worker;uint64_t deadline;unsigned visits;int complete;} ExchangeContext;
static int exchange(ExchangeContext *c,const Board *p,int target,int ply){
    c->visits++;if(c->visits>1000000||now_ms()>=c->deadline||(c->worker&&atomic_load_explicit(&c->worker->session->stop,memory_order_relaxed))){c->complete=0;if(c->worker&&c->worker->session->deadline&&now_ms()>=c->worker->session->deadline)atomic_store_explicit(&c->worker->session->stop,1,memory_order_relaxed);return 0;}
    if(ply>=64)return 0;Move moves[MAXMOVES];int n=generate(p,moves,1),best=0;
    uint64_t candidates=attackers(p,target,p->side);
    for(int i=0;i<n;i++){unsigned m=moves[i].m;int from=FROM(m);if(TO(m)!=target||!(candidates&(UINT64_C(1)<<((from>>4)*8+(from&7)))))continue;Board t;if(!make_move(p,m,&t))continue;int gain=rove_value[abs(p->b[target])];if(PROM(m))gain+=rove_value[PROM(m)]-rove_value[1];gain-=exchange(c,&t,target,ply+1);if(!c->complete)return 0;if(gain>best)best=gain;}
    return best;
}
static int see_for(Worker *w,const Board *p,unsigned m){atomic_fetch_add_explicit(&rove_see_calls,1,memory_order_relaxed);Board t;if(!make_move(p,m,&t))return -INF;uint64_t deadline=now_ms()+5000;if(w&&w->session->deadline&&w->session->deadline<deadline)deadline=w->session->deadline;ExchangeContext context={w,deadline,0,1};int gain=rove_value[abs(p->b[TO(m)])];if(abs(p->b[FROM(m)])==1&&TO(m)==p->ep&&!p->b[TO(m)])gain=100;if(PROM(m))gain+=rove_value[PROM(m)]-100;gain-=exchange(&context,&t,TO(m),0);return context.complete?gain:SEE_INCOMPLETE;}
int see(const Board *p,unsigned m){return see_for(NULL,p,m);}
static int stopped(Worker *w){
    if(atomic_load_explicit(&w->session->stop,memory_order_relaxed)||w->aborted)return 1;
    uint64_t n=atomic_load_explicit(&w->session->nodes,memory_order_relaxed);
    do{if(w->session->node_limit&&n>=w->session->node_limit){atomic_store_explicit(&w->session->stop,1,memory_order_relaxed);return 1;}}while(!atomic_compare_exchange_weak_explicit(&w->session->nodes,&n,n+1,memory_order_relaxed,memory_order_relaxed));w->nodes++;
    if((n&255)==0&&w->session->deadline&&now_ms()>=w->session->deadline){atomic_store_explicit(&w->session->stop,1,memory_order_relaxed);return 1;}return 0;
}
static int score_to_tt(int s,int ply){return s>MATE-MAXPLY?s+ply:s<-MATE+MAXPLY?s-ply:s;}
static int score_from_tt(int s,int ply){return s>MATE-MAXPLY?s-ply:s<-MATE+MAXPLY?s+ply:s;}
/* Bounds depend on both the halfmove clock and reversible position history. */
static uint64_t context_key(const Worker *w,const Board *p){uint64_t k=p->key^((uint64_t)p->half*UINT64_C(0xd6e8feb86659fd93));int start=w->path_len-p->half-1;if(start<0)start=0;for(int i=start;i<w->path_len;i++){k=(k<<17)|(k>>47);k^=w->path[i];}return k;}
static int tt_slot(_Atomic uint64_t *key_slot,_Atomic uint64_t *data_slot,uint64_t key,uint64_t *out){uint64_t d=atomic_load_explicit(data_slot,memory_order_relaxed),k=atomic_load_explicit(key_slot,memory_order_relaxed);if((k^d)!=key||!d||d!=atomic_load_explicit(data_slot,memory_order_relaxed))return 0;*out=d;return 1;}
static int tt_read(Worker *w,uint64_t key,uint64_t *data,int depth,int alpha,int ply){TTEntry *e=&w->table[key&w->table_mask];int found=tt_slot(&e->key,&e->data,key,data);
#if ROVE_VARIANT == 6
    uint64_t upper;if(tt_slot(&e->upper_key,&e->upper_data,key,&upper)&&(!found||(((upper>>33)&127)==(unsigned)depth&&score_from_tt((int16_t)(upper>>17),ply)<=alpha))){*data=upper;return 1;}
#else
    (void)depth;(void)alpha;(void)ply;
#endif
    return found;
}
static void tt_write(Worker *w,uint64_t key,unsigned move,int depth,int score,int bound,int ply){
    TTEntry *e=&w->table[key&w->table_mask];uint64_t d=(uint64_t)move|((uint64_t)(uint16_t)(int16_t)score_to_tt(score,ply)<<17)|((uint64_t)(depth<0?0:depth)<<33)|((uint64_t)bound<<40);
#if ROVE_VARIANT == 6
    if(bound==1||bound==3){atomic_store_explicit(&e->upper_data,d,memory_order_relaxed);atomic_store_explicit(&e->upper_key,key^d,memory_order_relaxed);}if(bound==3)return;
#endif
    atomic_store_explicit(&e->data,d,memory_order_relaxed);atomic_store_explicit(&e->key,key^d,memory_order_relaxed);
}
static int victim(const Board *p,unsigned m){int v=abs(p->b[TO(m)]);return !v&&abs(p->b[FROM(m)])==1&&TO(m)==p->ep?1:v;}
static int piece_index(int p){return p>0?p:6-p;}
static int is_capture(const Board *p,unsigned m){return victim(p,m)||PROM(m);}
static int move_score(Worker *w,const Board *p,unsigned m,unsigned tt,int ply){
    if(m==tt)return 2000000000;if(ply==w->hint_ply&&m==w->hint)return 1900000000;int v=victim(p,m),a=abs(p->b[FROM(m)]),s=0;
    if(v||PROM(m)){s=1000000+rove_value[v]*32-rove_value[a]+(PROM(m)?rove_value[PROM(m)]:0);
#if ROVE_VARIANT == 2
        int exchange_score=see_for(w,p,m);if(exchange_score!=SEE_INCOMPLETE)s+=exchange_score*32;
#endif
    }else{s=w->history[p->side<0][FROM(m)][TO(m)];if(ply&&w->previous[ply-1]){int prior=piece_index(-p->b[TO(w->previous[ply-1])]);if(prior<13)s+=w->continuation[prior][piece_index(p->b[FROM(m)])];}if(m==w->killers[ply][0])s+=500000;else if(m==w->killers[ply][1])s+=400000;}
#if ROVE_VARIANT == 5 || ROVE_MODEL
    s+=rove_model_order(p->b[FROM(m)],v,FROM(m),TO(m),PROM(m));
#endif
    if(w->id)s+=(int)((m*(unsigned)(w->id*17+13))&31);
    return s;
}
static int legal_witness(const Board *p,const Move *moves,int n){for(int i=0;i<n;i++){Board t;if(make_move(p,moves[i].m,&t))return 1;}return 0;}
static int qsearch(Worker *w,const Board *p,int alpha,int beta,int ply){
    if(stopped(w))return 0;if(ply>=MAXPLY-1){w->aborted=1;return 0;}if(ply>w->seldepth)w->seldepth=ply;w->pvlen[ply]=0;
    Move moves[MAXMOVES];int n=generate(p,moves,0),check=in_check(p);
    if(!legal_witness(p,moves,n))return check?-MATE+ply:0;
    if(drawn(p,w->path,w->path_len))return 0;
    int stand=evaluate(p),best=check?-INF:stand;if(!check){if(stand>=beta)return stand;if(stand>alpha)alpha=stand;}
    for(int i=0;i<n;i++)moves[i].score=move_score(w,p,moves[i].m,0,ply);
    for(int i=0;i<n;i++){int at=i;for(int j=i+1;j<n;j++)if(moves[j].score>moves[at].score)at=j;Move tmp=moves[i];moves[i]=moves[at];moves[at]=tmp;unsigned m=moves[i].m;if(!check&&!is_capture(p,m))continue;
#if ROVE_VARIANT == 2
        if(!check&&!PROM(m)){int exchange_score=see_for(w,p,m);if(exchange_score!=SEE_INCOMPLETE&&exchange_score<0)continue;}
#endif
        Board t;if(!make_move(p,m,&t))continue;w->path[w->path_len++]=t.key;w->previous[ply]=m;int s=-qsearch(w,&t,-beta,-alpha,ply+1);w->path_len--;if(w->aborted||atomic_load_explicit(&w->session->stop,memory_order_relaxed))return 0;if(s>best)best=s;if(s>alpha){alpha=s;w->pv[ply][0]=m;int len=w->pvlen[ply+1];memcpy(w->pv[ply]+1,w->pv[ply+1],(size_t)len*sizeof(unsigned));w->pvlen[ply]=len+1;if(alpha>=beta)break;}}
    return best;
}
int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,unsigned excluded,int learning){
    if(depth<=0)return qsearch(w,p,alpha,beta,ply);if(stopped(w))return 0;
    if(ply>=MAXPLY-1){w->aborted=1;return 0;}if(ply>w->seldepth)w->seldepth=ply;w->pvlen[ply]=0;
    int check=in_check(p);Move moves[MAXMOVES];int n=generate(p,moves,0);if(!legal_witness(p,moves,n))return check?-MATE+ply:0;
    if(drawn(p,w->path,w->path_len))return 0;
    if(alpha<-MATE+ply)alpha=-MATE+ply;if(beta>MATE-ply-1)beta=MATE-ply-1;if(alpha>=beta)return alpha;
    int oldalpha=alpha,best=-INF,count=0,ttdepth=-1,ttscore=0,ttbound=0;unsigned ttmove=0,bestmove=0;uint64_t data=0;
    uint64_t key=context_key(w,p);
#if ROVE_VARIANT == 6
    /* Different horizon depths have different minimax scores. A later go
     * must not merge last search's deeper bounds into a fresh shallow probe. */
    key^=(uint64_t)depth*UINT64_C(0xa0761d6478bd642f);
#endif
    if(!excluded&&tt_read(w,key,&data,depth,alpha,ply)){ttmove=(unsigned)(data&131071);ttdepth=(int)((data>>33)&127);ttscore=score_from_tt((int16_t)(data>>17),ply);ttbound=(int)((data>>40)&3);
#if ROVE_VARIANT == 6
        int eligible=ttdepth==depth;
#else
        int eligible=ttdepth>=depth;
#endif
        if(ply&&eligible&&(ttbound==1||(ttbound==2&&ttscore>=beta)||(ttbound==3&&ttscore<=alpha)))return ttscore;}
    int singular=0;
#if ROVE_VARIANT == 2
    if(!excluded&&ply&&depth>=6&&ttmove&&ttdepth>=depth-3&&(ttbound==1||ttbound==2)&&abs(ttscore)<MATE-MAXPLY){int threshold=ttscore-depth*2;atomic_fetch_add_explicit(&rove_singular_calls,1,memory_order_relaxed);int s=search(w,p,(depth-1)/2,threshold-1,threshold,ply,ttmove,0);if(w->aborted||atomic_load_explicit(&w->session->stop,memory_order_relaxed))return 0;singular=s<threshold;w->pvlen[ply]=0;}
#endif
    for(int i=0;i<n;i++)moves[i].score=move_score(w,p,moves[i].m,ttmove,ply);
    int static_eval=evaluate(p),corr=w->correction[p->side<0][p->pawnkey&1023]/64;
    for(int i=0;i<n;i++){int at=i;for(int j=i+1;j<n;j++)if(moves[j].score>moves[at].score)at=j;Move temp=moves[i];moves[i]=moves[at];moves[at]=temp;unsigned m=moves[i].m;if(m==excluded)continue;Board t;if(!make_move(p,m,&t))continue;
        int quiet=!is_capture(p,m);w->previous[ply]=m;w->path[w->path_len++]=t.key;int extension=singular&&m==ttmove;int nextdepth=depth-1+extension,s;
        if(!count)s=-search(w,&t,nextdepth,-beta,-alpha,ply+1,0,learning);
        else{int reduction=depth>=4&&count>=4&&quiet&&!check&&!in_check(&t)&&(static_eval+corr<alpha+100);
#if ROVE_VARIANT == 6
            reduction=0; /* MTD probes share a fixed, full-depth score contract. */
#endif
            s=-search(w,&t,nextdepth-reduction,-alpha-1,-alpha,ply+1,0,learning);if(s>alpha&&reduction)s=-search(w,&t,nextdepth,-alpha-1,-alpha,ply+1,0,learning);if(s>alpha&&s<beta)s=-search(w,&t,nextdepth,-beta,-alpha,ply+1,0,learning);}
        w->path_len--;if(w->aborted||atomic_load_explicit(&w->session->stop,memory_order_relaxed))return 0;count++;
        if(s>best){best=s;bestmove=m;}
        if(s>alpha){alpha=s;w->pv[ply][0]=m;int len=w->pvlen[ply+1];memcpy(w->pv[ply]+1,w->pv[ply+1],(size_t)len*sizeof(unsigned));w->pvlen[ply]=len+1;}
        if(alpha>=beta){if(learning&&quiet){int *h=&w->history[p->side<0][FROM(m)][TO(m)],bonus=depth*depth;*h+=bonus-(*h*bonus)/16384;if(w->killers[ply][0]!=m){w->killers[ply][1]=w->killers[ply][0];w->killers[ply][0]=m;}if(ply){int prior=piece_index(-p->b[TO(w->previous[ply-1])]);int cur=piece_index(p->b[FROM(m)]);if(prior<13){int *c=&w->continuation[prior][cur];*c+=bonus-(*c*bonus)/16384;}}}break;}
    }
    if(!count)return excluded?alpha:(check?-MATE+ply:0);
    if(!excluded){int bound=best>=beta?2:best<=oldalpha?3:1;tt_write(w,key,bestmove,depth,best,bound,ply);
#if ROVE_VARIANT != 6
        if(learning&&!check&&bestmove&&!is_capture(p,bestmove)&&bound==1&&abs(best)<MATE-MAXPLY){int error=best-static_eval;if(error>256)error=256;if(error< -256)error=-256;int *c=&w->correction[p->side<0][p->pawnkey&1023];*c+=error-*c/64;}
#endif
    }
    return best;
}
static void info(Worker *w,int depth,int score){
#if ROVE_DEV
    Session *s=w->session;pthread_mutex_lock(&s->mutex);uint64_t elapsed=now_ms()-s->start;printf("info depth %d seldepth %d score ",depth,w->seldepth);if(abs(score)>MATE-MAXPLY)printf("mate %d",score>0?(MATE-score+1)/2:-(MATE+score+1)/2);else printf("cp %d",score);printf(" nodes %llu time %llu pv",(unsigned long long)atomic_load_explicit(&s->nodes,memory_order_relaxed),(unsigned long long)elapsed);for(int i=0;i<w->pvlen[0];i++){char b[8];move_string(w->pv[0][i],b);printf(" %s",b);}puts("");fflush(stdout);pthread_mutex_unlock(&s->mutex);
#else
    (void)w;(void)depth;(void)score;
#endif
}
typedef struct {Session *session;Worker *workers;uint64_t generation;int groups;} ParallelContext;
static int parallel_stopped(void *arg){ParallelContext *c=arg;Session *s=c->session;if(s->deadline&&now_ms()>=s->deadline)atomic_store_explicit(&s->stop,1,memory_order_relaxed);return atomic_load_explicit(&s->stop,memory_order_relaxed);}
static RoveResult parallel_task(void *arg,const RoveTask *task,unsigned worker){
    ParallelContext *c=arg;Session *s=c->session;RoveResult r={0};r.first=task->first;
    if(task->generation!=c->generation||worker>=ROVE_WORKERS||parallel_stopped(arg))return r;
    Worker *w=&c->workers[worker];w->aborted=0;w->hint=0;w->hint_ply=-1;memcpy(w->path,s->history,(size_t)s->history_len*sizeof(uint64_t));w->path_len=s->history_len;
    size_t total=(size_t)1<<ROVE_TT_BITS,part=total;while(part*(size_t)task->groups>total)part>>=1;w->table=rove_tt+(size_t)task->group*part;w->table_mask=part-1;
    uint64_t before=w->nodes;int score;
    if(!task->first){score=search(w,&s->board,task->depth,task->alpha,task->beta,0,0,1);if(w->pvlen[0])r.first=w->pv[0][0];if(w->pvlen[0]>1)r.reply=w->pv[0][1];}
    else if(drawn(&s->board,w->path,w->path_len))score=0;
    else{Board child;if(!make_move(&s->board,task->first,&child))return r;w->path[w->path_len++]=child.key;w->previous[0]=task->first;
        if(task->kind==ROVE_COUNTERREPLY){Move moves[MAXMOVES];unsigned replies[MAXMOVES];int n=generate(&child,moves,0),count=0;for(int i=0;i<n;i++){Board t;if(moves[i].m!=task->reply&&make_move(&child,moves[i].m,&t))replies[count++]=moves[i].m;}if(!count)return r;unsigned reply=replies[worker%(unsigned)count];Board next;if(!make_move(&child,reply,&next))return r;w->path[w->path_len++]=next.key;w->previous[1]=reply;score=search(w,&next,task->depth-2,task->alpha,task->beta,2,0,0);r.reply=reply;}
        else{if(task->kind==ROVE_REPAIR){w->hint=task->reply;w->hint_ply=1;}score=-search(w,&child,task->depth-1,-task->beta,-task->alpha,1,0,1);if(w->pvlen[1])r.reply=w->pv[1][0];}
        w->path_len=s->history_len;
    }
    w->hint=0;w->hint_ply=-1;r.nodes=w->nodes-before;if(w->aborted||parallel_stopped(arg))return r;r.score=score;r.complete=1;r.bound=score<=task->alpha?ROVE_UPPER:score>=task->beta?ROVE_LOWER:ROVE_EXACT;return r;
}
static void run_parallel(Session *s,Worker *workers){
    Move generated[MAXMOVES];uint32_t moves[MAXMOVES];int n=generate(&s->board,generated,0),count=0;for(int i=0;i<n;i++){Board t;if(make_move(&s->board,generated[i].m,&t))moves[count++]=generated[i].m;}
    if(!count){s->score=in_check(&s->board)?-MATE:0;s->completed_depth=1;workers[0].seldepth=0;workers[0].pvlen[0]=0;info(&workers[0],1,s->score);return;}
    RoveParallelHistory history={0};unsigned priorfirst=s->best,priorreply=0;int guess=0;
    for(int depth=1;depth<=s->depth;depth++){
        for(int i=0;i<ROVE_WORKERS;i++)workers[i].seldepth=0;
        ParallelContext context={s,workers,s->generation*MAXPLY+(unsigned)depth,(ROVE_PARALLEL==2||ROVE_PARALLEL==4)?(ROVE_WORKERS+3)/4:1};
        /* Correction only steers LMR; scores remain on the same fixed evaluator. */
        for(int i=1;i<ROVE_WORKERS;i++)memcpy(workers[i].correction,workers[0].correction,sizeof workers[0].correction);
        RoveParallelResult result={0};
#if ROVE_VARIANT == 6
        int lower=-INF,upper=INF;unsigned converged_move=priorfirst,converged_reply=priorreply;int score=guess;
        while(lower<upper){int beta=score==lower?score+1:score;atomic_fetch_add_explicit(&rove_mtd_probes,1,memory_order_relaxed);result=rove_parallel_search(parallel_task,&context,moves,count,depth,beta-1,beta,priorfirst,priorreply,parallel_stopped,ROVE_WORKERS,ROVE_PARALLEL,context.generation,&history);s->assigned+=result.assigned;s->reassigned+=result.reassigned;s->reused+=result.reused;s->shared_bounds+=result.shared_bounds;s->clauses+=result.clauses;s->repairs+=result.repairs;if(!result.completedall||!result.best.complete||parallel_stopped(&context))break;score=result.best.score;if(score<lower||score>upper){atomic_fetch_add_explicit(&rove_mtd_conflicts,1,memory_order_relaxed);atomic_store_explicit(&s->stop,1,memory_order_relaxed);break;}if(score<beta)upper=score;else{lower=score;converged_move=result.best.first;converged_reply=result.best.reply;}}
        if(lower!=upper||!result.best.complete||parallel_stopped(&context))break;atomic_fetch_add_explicit(&rove_mtd_converged,1,memory_order_relaxed);result.best.score=score;result.best.first=converged_move;result.best.reply=converged_reply;
#else
        result=rove_parallel_search(parallel_task,&context,moves,count,depth,-INF,INF,priorfirst,priorreply,parallel_stopped,ROVE_WORKERS,ROVE_PARALLEL,context.generation,&history);
        if(!result.completedall||!result.best.complete||parallel_stopped(&context))break;
#endif
#if ROVE_VARIANT != 6
        s->assigned+=result.assigned;s->reassigned+=result.reassigned;s->reused+=result.reused;s->shared_bounds+=result.shared_bounds;s->clauses+=result.clauses;s->repairs+=result.repairs;
#endif
        s->parallel_mode=result.mode;s->groups=result.groups;
        s->score=result.best.score;s->completed_depth=depth;if(result.best.first)s->best=result.best.first;priorfirst=s->best;priorreply=result.best.reply;guess=s->score;
        for(int i=1;i<ROVE_WORKERS;i++)if(workers[i].seldepth>workers[0].seldepth)workers[0].seldepth=workers[i].seldepth;
        workers[0].pv[0][0]=s->best;workers[0].pvlen[0]=s->best?1:0;if(priorreply){workers[0].pv[0][1]=priorreply;workers[0].pvlen[0]=2;}info(&workers[0],depth,s->score);
        if(abs(s->score)>MATE-MAXPLY)break;
    }
}
void *session_run(void *arg){
    Session *s=arg;Worker *workers=s->workers;
    for(int i=0;i<ROVE_WORKERS;i++){workers[i].session=s;workers[i].id=i;workers[i].table=rove_tt;workers[i].table_mask=((size_t)1<<ROVE_TT_BITS)-1;workers[i].hint=0;workers[i].hint_ply=-1;}
    run_parallel(s,workers);
    char b[8];move_string(s->best,b);pthread_mutex_lock(&s->mutex);printf("bestmove %s\n",b);fflush(stdout);pthread_mutex_unlock(&s->mutex);return NULL;
}
