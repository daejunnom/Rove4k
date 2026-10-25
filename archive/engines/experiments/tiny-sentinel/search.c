#include "tiny.h"
#if DEV
#define COUNT(w,f) (++(w)->f)
#else
#define COUNT(w,f) ((void)0)
#endif

/* A slot is acquired without waiting. Contention is a miss, never a torn
 * key/payload publication. Search workers share slots, not mutable heuristics. */
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
static void learn(int16_t *cell,int bonus){
    *cell+=(bonus-*cell*abs(bonus)/16384);
}
/* A bijection of the 12 real piece codes plus empty; EDGE is never a mover. */
static int piece_index(int p){return TYPE(p)+6*SIDE(p);}
static int capture(const Board *p,Move m){return p->b[TO(m)]||
    (TYPE(p->b[FROM(m)])==1&&TO(m)==p->e);}
static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,Move previous,Move *root){
    if(!claim(w))return 0;
    int check=attacked(p,p->k[SIDE(p->s)],OTHER(p->s)),draw=p->half>=100;
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
    int evaluation=p->s==WHITE?p->v:-p->v;
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
    int prior=previous?piece_index(p->b[TO(previous)]):0;
    for(int i=0;i<count;i++){
        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);
        scores[i]=m==tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
            w->history[from][to]+w->continuation[prior][pi]+(int)((ORDER_MOVE(m)*37u+w->id*19u)%17);
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
            int reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[SIDE(q.s)],OTHER(q.s));
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
        int error=best-(p->s==WHITE?p->v:-p->v);if(error>256)error=256;if(error< -256)error=-256;
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
    w->nodes=0;w->depth=0;w->score=0;
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
