#ifndef TINY_H
#define TINY_H
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <limits.h>

#ifndef WORKERS
#define WORKERS 2
#endif
#ifndef TT_BITS
#define TT_BITS 18
#endif
#ifndef DEV
#define DEV 0
#endif
#ifndef PLY
#define PLY 128
#endif
/* Admission preserves <=16 pieces/side; each piece has <=27 pseudo moves,
 * including all promotions/castles, so the conservative bound is 432. */
#define MOVES 512
#define HISTORY 4096
#define MATE 30000
typedef unsigned Move;
/* 0x88: a1=0, h8=119. Signed P/N/B/R/Q/K = 1..6, white positive.
 * h is the FIDE repetition key, v incremental white HCE, r the reversible
 * path digest used only for TT context. e=-1 means no LEGAL en passant.
 */
typedef struct { int8_t b[128]; int s,c,e,k[2],half
#if DEV
,v
#endif
; uint64_t h,r; } Board;
#if DEV
#endif
#define FROM(m) ((m)&127)
#define TO(m) (((m)>>7)&127)
#define PROMO(m) (((m)>>14)&7)
#define MOVE(f,t,p) ((Move)(f)|((Move)(t)<<7)|((Move)(p)<<14))

typedef struct { atomic_flag lock; uint64_t key,data; } Entry;
typedef struct {
    int id,depth,score; Move best;
    uint64_t nodes,keys[HISTORY+PLY]; int length;
    int16_t history[128][128],continuation[13][13],correction[1024];
#if DEV
    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts;
#endif
} Worker;
#if DEV
#endif
#endif

Entry *table;
Worker workers[WORKERS];
atomic_int stopped;
#if DEV
atomic_uint_fast64_t searched;
uint64_t limit;
int max_depth;
#endif
uint64_t deadline,game_keys[HISTORY];
int game_length;
Board position;
#include "rove-common/protocol/now"

#if DEV
#include <ctype.h>
#include <errno.h>
#endif

/* A's mailbox is the only board representation. No bitboard or hash table
 * initialization is required. Piece and state key domains do not overlap. */
static const int steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};
#include "rove-common/board/mix"
#include "rove-common/board/value_scalar"
#include "rove-common/board/piece"
#include "rove-common/board/state"
#include "rove-common/board/put_dev_evaluation"
static int walk(const Board *,Move *,int,int);
#include "rove-common/move/attacked"
#include "rove-common/board/dead"
/* Canonicalize EP before storing a position: an uncapturable target, including
 * one whose capture exposes the king, must not distinguish repetition keys. */
#include "rove-common/board/ep"
#include "rove-common/board/rights"
/* Internal contract: p came from start/FEN/a prior successful make, and m
 * belongs to gen(p). Both runtimes parse through gen+make; search, perft and
 * fallback only apply list members (a TT move only changes their ordering).
 * Thus gen proves valid endpoints, side/occupancy, pawn promotion geometry,
 * and the castle origin/transit safety. start/FEN plus rights(from)|rights(to) prove
 * the castle rook exists; normalized EP proves its captured pawn exists.
 * Keep the king-capture prohibition: gen includes attacked king squares.
 * Keep the resulting own-king test: ordinary pins, EP discoveries and castle
 * destination attacks are intentionally filtered only after applying a move. */
#include "rove-common/move/make"
#include "rove-common/move/add"
/* Both modes walk forward from pieces of side s. A null output list asks
 * whether any geometric attack reaches sq, even if sq holds a friendly piece.
 * Pawn pushes and castling belong only to move generation, never attacks. */
#include "rove-common/move/walk"
#include "rove-common/move/gen"
#include "rove-common/board/start"
#if DEV
#include "rove-common/board/fen"
int verify_board(const Board *p){
    if((p->s!=1&&p->s!=-1)||p->c<0||p->c>15||p->half<0||p->e<-1)return 0;
    Board t={0};t.s=p->s;t.c=p->c;t.e=p->e;t.k[0]=t.k[1]=-1;int kings[2]={0},counts[2]={0};
    for(int q=0;q<128;q++){
        int v=p->b[q];if(abs(v)>6||((q&0x88)&&v))return 0;
        if(v){if(++counts[v<0]>16)return 0;put(&t,q,v);if(abs(v)==6)kings[v<0]++;}
    }
    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v)return 0;
    for(int i=0;i<4;i++)if(t.c&(1<<i)){
        int home=i<2?4:116,rook=(i&1)?home-4:home+3,side=i<2?1:-1;
        if(t.b[home]!=side*6||t.b[rook]!=side*4)return 0;
    }
    if(t.e>=0&&((t.e&0x88)||(t.e>>4)!=(t.s>0?5:2)||t.b[t.e]||t.b[t.e-t.s*16]!=-t.s))return 0;
    ep(&t);return t.e==p->e&&p->h==(t.h^state(&t));
}
#endif


/* C lookup experiment: signed-piece/square HCE, either constructed once at
 * startup or inserted as an exact read-only table by the recipe generator. */
#include <immintrin.h>
static int32_t tiny_table[13*64];
#if DEV
static atomic_uint_fast64_t tiny_leaf_calls,tiny_order_calls,tiny_init_calls;
static int tiny_scalar(const Board *p){
    int score=0;
    for(int q=0;q<128;q++)if(!(q&0x88)&&p->b[q])score+=value(p->b[q],q);
    return score;
}
#endif
static void __attribute__((constructor)) tiny_eval_init(void){
#if DEV
    atomic_fetch_add_explicit(&tiny_init_calls,1,memory_order_relaxed);
#endif
    for(int v=-6;v<=6;v++)for(int q=0;q<64;q++)tiny_table[(v+6)*64+q]=value(v,(q/8)*16+q%8);
}
static int tiny_raw(const Board *p){
    __m256i sum=_mm256_setzero_si256(),base=_mm256_setr_epi32(384,385,386,387,388,389,390,391);
#if DEV
    atomic_fetch_add_explicit(&tiny_leaf_calls,1,memory_order_relaxed);
#endif
    for(int q=0;q<128;q+=16){
        __m256i pieces=_mm256_cvtepi8_epi32(_mm_loadl_epi64((const __m128i *)(p->b+q)));
        __m256i index=_mm256_add_epi32(base,_mm256_slli_epi32(pieces,6));
        sum=_mm256_add_epi32(sum,_mm256_i32gather_epi32(tiny_table,index,4));
        base=_mm256_add_epi32(base,_mm256_set1_epi32(8));
    }
    __m128i half=_mm_add_epi32(_mm256_castsi256_si128(sum),_mm256_extracti128_si256(sum,1));
    half=_mm_hadd_epi32(half,half);
    return _mm_cvtsi128_si32(_mm_hadd_epi32(half,half));
}
static int tiny_order(const Board *p,Move m){(void)p;(void)m;return 0;}

#if DEV
#define COUNT(w,f) (++(w)->f)
#else
#define COUNT(w,f) ((void)0)
#endif

/* A slot is acquired without waiting. Contention is a miss, never a torn
 * key/payload publication. Search workers share slots, not mutable heuristics. */
#include "rove-common/search/probe_explicit_write"
#include "rove-common/search/claim"
#include "rove-common/search/learn_signed"
#include "rove-common/search/piece_index"
#include "rove-common/move/capture"
static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,Move previous,Move *root){
    if(!claim(w))return 0;
    int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;
    /* Only positions since the last irreversible move may repeat. Current h
     * already ends the path. Two earlier occurrences make the third visit. */
    int repetitions=0,end=w->length-1-p->half;
    if(end<0)end=0;
    for(int i=w->length-3;i>=end;i-=2)repetitions+=w->keys[i]==p->h;
    draw|=repetitions>=2||dead(p);
    Move moves[MOVES],bestmove=0;
    int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;
    /* Bounds have one fixed leaf meaning across workers. Correction changes
     * selective reduction eligibility, never the shared TT's integer scale. */
    int evaluation=p->s*tiny_raw(p);
    if(evaluation>MATE-PLY-1)evaluation=MATE-PLY-1;
    if(evaluation< -MATE+PLY+1)evaluation=-MATE+PLY+1;
    if(draw||ply==PLY-1){
        Board q;
        for(int i=0;i<count;i++)if(make(p,moves[i],&q)){
            if(!draw){COUNT(w,ply_aborts);atomic_store(&stopped,1);}
            return 0;
        }
        return check?-MATE+ply:0;
    }
    uint64_t key=p->h^mix(p->r+(unsigned)p->half),data=probe(key,0,0);
    Move tt=data&131071;
    int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;
    if(bound)COUNT(w,hits);
    if(score>MATE-PLY)score-=ply;
    if(score< -MATE+PLY)score+=ply;
    if(ply&&bound&&ttdepth>=(depth>0?depth:0)&&
       (bound==1||(bound==2&&score>=beta)||(bound==3&&score<=alpha)))return score;
    if(depth<=0)COUNT(w,qs);
    int quiet=depth<=0&&!check;
    if(quiet){best=evaluation;if(best>alpha)alpha=best;}
    int prior=previous?piece_index(p->b[TO(previous)]):6;
    for(int i=0;i<count;i++){
        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);
        scores[i]=m==tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
            w->history[from][to]+w->continuation[prior][pi]+(int)((m*37u+w->id*19u)%17);
        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;
        scores[i]+=tiny_order(p,m);
    }
    for(int i=0;i<count;i++){
        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;
        Move m=moves[j];moves[j]=moves[i];moves[i]=m;
        int t=scores[j];scores[j]=scores[i];scores[i]=t;
        Board q;if(!make(p,m,&q))continue;
        ++legal;
        int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m);
        if(quiet&&(!tactical||alpha>=beta))continue;
        w->keys[w->length++]=q.h;
        if(legal==1||depth<=0)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,m,0);
        else{
            COUNT(w,pvs);
            int reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s);
            if(reduce){COUNT(w,corr_uses);reduce=evaluation+w->correction[p->h&1023]/64<alpha+100;}
            score=-search(w,&q,depth-1-reduce,-alpha-1,-alpha,ply+1,m,0);
            if(reduce&&score>alpha)score=-search(w,&q,depth-1,-alpha-1,-alpha,ply+1,m,0);
            if(score>alpha&&score<beta)score=-search(w,&q,depth-1,-beta,-alpha,ply+1,m,0);
        }
        --w->length;
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        if(score>best){best=score;bestmove=m;if(root)*root=m;}
        if(score>alpha)alpha=score;
        if(alpha>=beta){
            if(depth>0&&!tactical){
                int bonus=depth*depth;
                learn(&w->history[from][to],bonus);
                learn(&w->continuation[prior][piece_index(p->b[from])],bonus);
                COUNT(w,hist_updates);COUNT(w,cont_updates);
            }
            break;
        }
    }
    if(!legal)return check?-MATE+ply:0;
    bound=best<=old?3:best>=beta?2:1;
    if(depth>0&&bound==1&&!check&&bestmove&&!capture(p,bestmove)&&!PROMO(bestmove)&&abs(best)<MATE-PLY){
        int error=best-evaluation;if(error>256)error=256;if(error< -256)error=-256;
        w->correction[p->h&1023]+=error-w->correction[p->h&1023]/64;
        COUNT(w,corr_updates);
    }
    score=best;
    if(score>MATE-PLY)score+=ply;
    if(score< -MATE+PLY)score-=ply;
    data=bestmove|((uint64_t)(uint16_t)score<<17)|((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);
    probe(key,1,data);return best;
}
void think(Worker *w,const Board *p){
    w->nodes=0;w->depth=0;w->score=0;w->best=0;
    w->length=game_length;
    memcpy(w->keys,game_keys,game_length*sizeof(uint64_t));
    /* Each worker explores a different move tie order; each completed PVS
     * iteration still covers the full root and publishes a legal witness. */
    for(int depth=1;depth<=
#if DEV
        max_depth
#else
        PLY-2
#endif
        ;depth++){
        Move best=w->best;
        int score=search(w,p,depth,-MATE,MATE,0,0,&best);
        if(atomic_load_explicit(&stopped,memory_order_relaxed))break;
        w->best=best;w->score=score;w->depth=depth;
    }
}




static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t command=PTHREAD_COND_INITIALIZER,finished=PTHREAD_COND_INITIALIZER;
static unsigned epoch;
static int pending=WORKERS,quitting;
static Move fallback;

#include "rove-common/protocol/text"
#include "rove-common/protocol/parse_with_board"
#include "rove-common/protocol/result"
#include "rove-common/protocol/work_pending_start"
#include "rove-common/protocol/wait"
#include "rove-common/protocol/clear"
#include "rove-common/protocol/set_position_with_board"
#include "rove-common/protocol/number"
#include "rove-common/protocol/read_line"
#include "rove-common/protocol/go_with_board"
#if DEV
static uint64_t perft(const Board *b,int d){
    if(!d)return 1;
    uint64_t total=0;Move list[MOVES];Board c;int n=gen(b,list);
    for(int i=0;i<n;i++)if(make(b,list[i],&c))total+=perft(&c,d-1);
    return total;
}
static int drawn(void){int n=0;for(int i=0;i<game_length;i++)n+=game_keys[i]==position.h;return position.half>=100||n>=3||dead(&position);}
static void stats(void){
    uint64_t pvs=0,qs=0,hits=0,hist=0,cont=0,corr=0,uses=0,aborts=0;int depth=0;
    for(int i=0;i<WORKERS;i++){
        Worker *w=workers+i;if(w->depth>depth)depth=w->depth;
        pvs+=w->pvs;qs+=w->qs;hits+=w->hits;hist+=w->hist_updates;cont+=w->cont_updates;corr+=w->corr_updates;uses+=w->corr_uses;aborts+=w->ply_aborts;
    }
    printf("{\"workers\":%d,\"total_threads\":%d,\"nodes\":%llu,\"completed_depth\":%d,\"pvs\":%llu,\"qs\":%llu,\"tt_hits\":%llu,\"history_updates\":%llu,\"continuation_updates\":%llu,\"correction_updates\":%llu,\"correction_uses\":%llu,\"ply_aborts\":%llu,\"leaf_calls\":%llu,\"ordering_calls\":%llu}\n",WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched),depth,(unsigned long long)pvs,(unsigned long long)qs,(unsigned long long)hits,(unsigned long long)hist,(unsigned long long)cont,(unsigned long long)corr,(unsigned long long)uses,(unsigned long long)aborts,(unsigned long long)atomic_load(&tiny_leaf_calls),(unsigned long long)atomic_load(&tiny_order_calls));fflush(stdout);
}
#endif
int main(void){
    pthread_t threads[WORKERS];int created=0,status=0;char line[32768];
    table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;clear();start(&position);game_keys[0]=position.h;game_length=1;
    for(;created<WORKERS;created++){workers[created].id=created;if(pthread_create(threads+created,NULL,work,workers+created)){status=2;goto shutdown;}}
    wait();
    for(;;){
        int status=read_line(line);if(status<0)break;if(!status)continue;
        size_t n=strlen(line);
        while(n&&(line[n-1]=='\n'||line[n-1]=='\r'||line[n-1]==' '||line[n-1]=='\t'))line[--n]=0;
        if(!strcmp(line,"uci")){
#if DEV
            puts("id name Rove4k C\nuciok");
#else
            puts("uciok");
#endif
            fflush(stdout);
        }
        else if(!strcmp(line,"isready")){puts("readyok");fflush(stdout);}
        else if(!strcmp(line,"quit"))break;
#if DEV
        else if(!strcmp(line,"stop"))wait();
        else if(!strcmp(line,"ucinewgame")){wait();clear();}
#endif
        else if(!strncmp(line,"position ",9)){wait();set_position(line+9);}
        else if(!strcmp(line,"go")||!strncmp(line,"go ",3))go(line+2);
#if DEV
        else if(!strncmp(line,"perft ",6)){wait();uint64_t d=number(line+6);if(d<=8)printf("perft %d %llu\n",(int)d,(unsigned long long)perft(&position,d));fflush(stdout);}
        else if(!strcmp(line,"legal")){wait();Move list[MOVES];Board b;int count=gen(&position,list);printf("legal");for(int i=0;i<count;i++)if(make(&position,list[i],&b)){char s[6];text(list[i],s);printf(" %s",s);}puts("");fflush(stdout);}
        else if(!strcmp(line,"eval")){wait();printf("eval %d\n",tiny_raw(&position)*position.s);fflush(stdout);}
        else if(!strcmp(line,"state")){wait();printf("{\"hash\":\"%016llx\",\"halfmove\":%d,\"eval\":%d,\"draw\":%s,\"invariant\":%s}\n",(unsigned long long)position.h,position.half,tiny_raw(&position)*position.s,drawn()?"true":"false",verify_board(&position)?"true":"false");fflush(stdout);}
        else if(!strcmp(line,"verify")){wait();Move list[MOVES];Board b;int good=verify_board(&position),count=gen(&position,list),tested=1;for(int i=0;i<count;i++)if(make(&position,list[i],&b)){good&=verify_board(&b);tested++;}printf("verify %s positions %d\n",good?"pass":"fail",tested);fflush(stdout);}
        else if(!strcmp(line,"stats")){wait();stats();}
#endif
    }
    wait();
shutdown:
    pthread_mutex_lock(&mutex);quitting=1;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
    for(int i=0;i<created;i++)if(pthread_join(threads[i],NULL))status=2;
    free(table);return status;
}
