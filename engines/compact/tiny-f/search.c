#include "tiny.h"
#if DEV
#define COUNT(w,f) (++(w)->f)
#else
#define COUNT(w,f) ((void)0)
#endif

/* Full 64-bit keys and payloads are read/written under this one try-lock.
 * A busy slot is a miss. This single-bound implementation never combines a
 * later upper-only move with a previous lower-bound root witness. */
static uint64_t probe(uint64_t key,int write,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;
    if(write)e->key=key,e->data=data;
    else data=e->key==key?e->data:0;
    atomic_flag_clear_explicit(&e->lock,memory_order_release);
    return data;
}
static int claim(Worker *w){
    if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
    if(!(w->nodes&255)&&now()>=deadline){atomic_store(&stopped,1);return 0;}
#if DEV
    if(limit){
        uint64_t n=atomic_load_explicit(&searched,memory_order_relaxed);
        do{if(n>=limit){atomic_store(&stopped,1);return 0;}}
        while(!atomic_compare_exchange_weak_explicit(&searched,&n,n+1,memory_order_relaxed,memory_order_relaxed));
    }else atomic_fetch_add_explicit(&searched,1,memory_order_relaxed);
#endif
    ++w->nodes;return 1;
}
static void learn(int16_t *cell,int bonus){*cell+=bonus-*cell*abs(bonus)/16384;}
static int piece_index(int p){return p+6;}
static int capture(const Board *p,Move m){return p->b[TO(m)]||
    (abs(p->b[FROM(m)])==1&&TO(m)==p->e);}
static int quiet_score(Worker *w,const Board *p,Move m,int prior){
    int from=FROM(m),to=TO(m),correction=w->correction[(p->h^m)&1023]/64;
    if(correction)COUNT(w,corr_uses);
    return w->history[from][to]+w->continuation[prior][piece_index(p->b[from])]+
        correction+(int)((m*37u+w->id*19u)%17);
}
static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,Move previous,Move *root){
    if(!claim(w))return 0;
    int check=attacked(p,p->k[p->s<0],-p->s),draw=p->half>=100;
    int repetitions=0,end=w->length-1-p->half;
    if(end<0)end=0;
    for(int i=w->length-3;i>=end;i-=2)repetitions+=w->keys[i]==p->h;
    draw|=repetitions>=2||dead(p);
    Move moves[MOVES],bestmove=0;
    int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;
    /* Correction/history affect ordering only. Every completed bound refers
     * to full-depth PVS plus this fixed raw-HCE quiescence leaf contract. */
    int evaluation=p->s*p->v;
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
    /* Horizon 0 is QS; positive horizons are exactly the requested depth.
     * Neither deeper normal bounds nor normal bounds in QS are admissible.
     * Root cutoffs remain disabled, so fail-high returns a searched witness. */
    if(ply&&bound&&ttdepth==(depth>0?depth:0)&&
       (bound==1||(bound==2&&score>=beta)||(bound==3&&score<=alpha)))return score;
    if(depth<=0)COUNT(w,qs);
    int quiet=depth<=0&&!check;
    if(quiet){best=evaluation;if(best>alpha)alpha=best;}
    int prior=previous?piece_index(p->b[TO(previous)]):6;
    for(int i=0;i<count;i++){
        Move m=moves[i];int from=FROM(m),to=TO(m);
        scores[i]=m==tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
            quiet_score(w,p,m,prior);
        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;
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
            score=-search(w,&q,depth-1,-alpha-1,-alpha,ply+1,m,0);
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
    score=best;
    if(score>MATE-PLY)score+=ply;
    if(score< -MATE+PLY)score-=ply;
    data=bestmove|((uint64_t)(uint16_t)score<<17)|((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);
    probe(key,1,data);return best;
}
void think(Worker *w,const Board *p){
    w->nodes=0;w->depth=0;w->score=0;
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
            score=search(w,p,depth,beta-1,beta,0,0,&move);
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
