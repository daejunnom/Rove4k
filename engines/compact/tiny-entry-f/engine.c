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
typedef struct { int8_t b[128]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;
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
    uint64_t f_probes,f_lower,f_upper,f_converged,f_conflicts,f_upper_other;
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
#include "rove-common/board/put_scalar"
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

#if MATE-PLY-1<=32*910
#error admitted HCE exceeds static bound
#endif

#if DEV
#define COUNT(w,f) (++(w)->f)
#else
#define COUNT(w,f) ((void)0)
#endif

/* Full 64-bit keys and payloads are read/written under this one try-lock.
 * A busy slot is a miss. This single-bound implementation never combines a
 * later upper-only move with a previous lower-bound root witness. */
#include "rove-common/search/probe"
#include "rove-common/search/claim"
static void learn(int16_t *cell,int bonus){*cell+=bonus-*cell*bonus/16384;}
#include "rove-common/search/piece_index"
#include "rove-common/move/capture"
static int quiet_score(Worker *w,const Board *p,Move m,int prior){
    int from=FROM(m),to=TO(m),correction=w->correction[(p->h^m)&1023]/64;
    if(correction)COUNT(w,corr_uses);
    return w->history[from][to]+w->continuation[prior][piece_index(p->b[from])]+
        correction+(int)((m*37u+w->id*19u)%17);
}
static int search(Worker *w,const Board *p,int depth,int beta,int ply,int prior,Move *root){
    if(!claim(w))return 0;
    int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;
    int repetitions=0,end=w->length-1-p->half;
    if(end<0)end=0;
    for(int i=w->length-3;i>=end;i-=2)repetitions+=w->keys[i]==p->h;
    draw|=repetitions>=2||dead(p);
    Move moves[MOVES],bestmove=0;
    int scores[MOVES],count=gen(p,moves),legal=0,best=-MATE;
    /* Correction/history affect ordering only. Every completed bound refers
     * to full-depth PVS plus this fixed raw-HCE quiescence leaf contract. */
    int evaluation=p->s*p->v;
    if(draw||ply==PLY-1){
        Board q;
        for(int i=0;i<count;i++)if(make(p,moves[i],&q)){
            if(!draw){COUNT(w,ply_aborts);atomic_store(&stopped,1);}
            return 0;
        }
        return check?-MATE+ply:0;
    }
    uint64_t key=p->h^mix(p->r+(unsigned)p->half),data=probe(key,0);
    Move tt=data&131071;
    int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;
    if(bound)COUNT(w,hits);
    if(score>MATE-PLY)score-=ply;
    if(score< -MATE+PLY)score+=ply;
    /* Horizon 0 is QS; positive horizons are exactly the requested depth.
     * Neither deeper normal bounds nor normal bounds in QS are admissible.
     * Root cutoffs remain disabled, so fail-high returns a searched witness. */
    if(ply&&bound&&ttdepth==(depth>0?depth:0)&&
       (bound==1||(bound==2&&score>=beta)||(bound==3&&score<beta)))return score;
    if(depth<=0)COUNT(w,qs);
    int quiet=depth<=0&&!check;
    if(quiet)best=evaluation;
    for(int i=0;i<count;i++){
        Move m=moves[i];int from=FROM(m),to=TO(m);
        scores[i]=m==tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
            quiet_score(w,p,m,prior);
        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;
    }
    for(int i=0;i<count;i++){
        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;
        Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];
        Board q;if(!make(p,m,&q))continue;
        ++legal;
        int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m),next=piece_index(q.b[to]);
        if(quiet&&(!tactical||best>=beta))continue;
        w->keys[w->length++]=q.h;
#if DEV
        /* Retain the nonfirst-normal-probe observation in DEV only. */
        if(legal>1&&depth>0)COUNT(w,pvs);
#endif
        score=-search(w,&q,depth-1,1-beta,ply+1,next,0);
        --w->length;
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        if(score>best){best=score;bestmove=m;if(root)*root=m;}
        if(score>=beta){
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
    bound=best>=beta?2:3;
    score=best;
    if(score>MATE-PLY)score+=ply;
    if(score< -MATE+PLY)score-=ply;
    data=bestmove|((uint64_t)(uint16_t)score<<17)|((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);
    probe(key,data);return best;
}
void think(Worker *w,const Board *p){
    w->nodes=0;w->depth=0;w->score=0;w->best=0;
    w->length=game_length;
    memcpy(w->keys,game_keys,game_length*sizeof(uint64_t));
    for(int depth=1;depth<=
#if DEV
        max_depth
#else
        PLY-2
#endif
        ;depth++){
        int lower=-MATE,upper=MATE,score=w->score;
        Move witness=w->best;
        while(lower<upper){
            int beta=score==lower?score+1:score;
            Move move=0;COUNT(w,f_probes);
            score=search(w,p,depth,beta,0,6,&move);
            if(atomic_load_explicit(&stopped,memory_order_relaxed))break;
            if(score<lower||score>upper){COUNT(w,f_conflicts);atomic_store(&stopped,1);break;}
            if(score<beta){upper=score;COUNT(w,f_upper);
#if DEV
                if(move&&witness&&move!=witness)w->f_upper_other++;
#endif
            }
            else{lower=score;if(move)witness=move;COUNT(w,f_lower);}
        }
        if(lower!=upper||atomic_load_explicit(&stopped,memory_order_relaxed))break;
        COUNT(w,f_converged);
        w->best=witness;w->score=score;w->depth=depth;
        if(witness&&!attacked(p,p->k[p->s<0],-p->s)&&!capture(p,witness)&&!PROMO(witness)&&abs(score)<MATE-PLY){
            int error=score-p->s*p->v;if(error>256)error=256;if(error< -256)error=-256;
            int16_t *cell=&w->correction[(p->h^witness)&1023];*cell+=error-*cell/64;
            COUNT(w,corr_updates);
        }
    }
}




static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t command=PTHREAD_COND_INITIALIZER,finished=PTHREAD_COND_INITIALIZER;
static unsigned epoch;
static int pending=WORKERS,quitting;
static Move fallback;

#include "rove-common/protocol/text"
static Move parse(const Board *b,const char *s,Board *c){
    Move list[MOVES];char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(list[i],name);if((!s||!strcmp(s,name))&&make(b,list[i],c))return list[i];}return 0;
}
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
    uint64_t f_probes=0,f_lower=0,f_upper=0,f_converged=0,f_conflicts=0,f_upper_other=0;
    for(int i=0;i<WORKERS;i++){
        Worker *w=workers+i;if(w->depth>depth)depth=w->depth;
        f_probes+=w->f_probes;f_lower+=w->f_lower;f_upper+=w->f_upper;f_converged+=w->f_converged;f_conflicts+=w->f_conflicts;f_upper_other+=w->f_upper_other;
        pvs+=w->pvs;qs+=w->qs;hits+=w->hits;hist+=w->hist_updates;cont+=w->cont_updates;corr+=w->corr_updates;uses+=w->corr_uses;aborts+=w->ply_aborts;
    }
    printf("{\"f_probes\":%llu,\"f_lower\":%llu,\"f_upper\":%llu,\"f_converged\":%llu,\"f_conflicts\":%llu,\"f_upper_other\":%llu,\"workers\":%d,\"total_threads\":%d,\"nodes\":%llu,\"completed_depth\":%d,\"pvs\":%llu,\"qs\":%llu,\"tt_hits\":%llu,\"history_updates\":%llu,\"continuation_updates\":%llu,\"correction_updates\":%llu,\"correction_uses\":%llu,\"ply_aborts\":%llu}\n",(unsigned long long)f_probes,(unsigned long long)f_lower,(unsigned long long)f_upper,(unsigned long long)f_converged,(unsigned long long)f_conflicts,(unsigned long long)f_upper_other,WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched),depth,(unsigned long long)pvs,(unsigned long long)qs,(unsigned long long)hits,(unsigned long long)hist,(unsigned long long)cont,(unsigned long long)corr,(unsigned long long)uses,(unsigned long long)aborts);fflush(stdout);
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
            puts("id name Rove4k F full-depth MTD\nuciok");
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
        else if(!strcmp(line,"eval")){wait();printf("eval %d\n",position.v*position.s);fflush(stdout);}
        else if(!strcmp(line,"state")){wait();printf("{\"hash\":\"%016llx\",\"halfmove\":%d,\"eval\":%d,\"draw\":%s,\"invariant\":%s}\n",(unsigned long long)position.h,position.half,position.v*position.s,drawn()?"true":"false",verify_board(&position)?"true":"false");fflush(stdout);}
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
