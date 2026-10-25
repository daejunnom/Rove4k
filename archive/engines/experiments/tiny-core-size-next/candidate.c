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
#if PLY > 879
#error admitted HCE bound overlaps mate scale
#endif
#define MOVES 512
#define HISTORY 4096
#define MATE 30000
typedef unsigned Move;
/* 0x88: a1=0, h8=119. Signed P/N/B/R/Q/K = 1..6, white positive.
 * h is the FIDE repetition key, v incremental white HCE, r the reversible
 * path digest used only for TT context. e=-1 means no LEGAL en passant.
 */
typedef struct { int8_t b[128]; uint64_t bb[2][7]; int s,c,e,k[2],half,v; uint64_t h,r; } Board;
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
    uint64_t pvs,qs,hits,hist_updates,cont_updates,corr_updates,corr_uses,ply_aborts,see_calls,see_incomplete,singular_calls,extensions;
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
uint64_t now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}

#if DEV
#include <ctype.h>
#include <errno.h>
#endif

/* B maintains mailbox plus piece and occupied bitboards in put().
 * King safety and exact legal exchange share attackers(). */
static const int steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};
uint64_t mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
int value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[a]+advance*(a==1?7:a==4?2:0)+
        center*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
    return v>0?score:-score;
}
static uint64_t bit(int q){return UINT64_C(1)<<((q>>4)*8+(q&7));}
static uint64_t piece(int v,int q){return mix((uint64_t)(q+(v+6)*128));}
static uint64_t state(const Board *p){
    return mix(2048+p->c)^(p->s<0?mix(2064):0)^
        (p->e<0?0:mix(2065+(p->e&7)));
}
static void put(Board *p,int q,int v){
    for(int old=p->b[q],sign=-1;sign<2;sign+=2,old=v)if(old){
        p->bb[old<0][abs(old)]^=bit(q);p->bb[old<0][0]^=bit(q);
        p->h^=piece(old,q);p->v+=sign*value(old,q);
    }
    p->b[q]=(int8_t)v;if(abs(v)==6)p->k[v<0]=q;
}
/* The same incrementally maintained bitboards supply king safety and SEE.
 * Geometric attackers may be pinned: legal make() rejects their recaptures. */
static uint64_t attackers(const Board *p,int sq,int side){
    int c=side<0;uint64_t result=0,occupied=p->bb[0][0]|p->bb[1][0];
    for(int d=-1;d<=1;d+=2){int q=sq-side*16+d;if(!(q&0x88))result|=p->bb[c][1]&bit(q);}
    for(int i=0;i<8;i++){
        int q=sq+steps[i];if(!(q&0x88))result|=p->bb[c][2]&bit(q);
        q=sq+steps[i+8];if(!(q&0x88))result|=p->bb[c][6]&bit(q);
        for(q=sq+steps[i+8];!(q&0x88);q+=steps[i+8]){
            uint64_t b=bit(q);
            if(occupied&b){result|=b&(p->bb[c][5]|p->bb[c][i<4?4:3]);break;}
        }
    }
    return result;
}
int attacked(const Board *p,int sq,int side){return attackers(p,sq,side)!=0;}
int dead(const Board *p){
    int minors=0,knights=0,colors=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){minors++;knights++;}
        else if(a==3){minors++;colors|=1<<((q+(q>>4))&1);}
        else if(a&&a<6)return 0;
    }
    return minors<2||(!knights&&colors!=3);
}
/* Canonicalize EP before storing a position: an uncapturable target, including
 * one whose capture exposes the king, must not distinguish repetition keys. */
static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t=*p;put(&t,q,0);put(&t,p->e-p->s*16,0);put(&t,p->e,p->s);
            if(!attacked(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}
static int rights(int q){return q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}
/* Internal contract: p came from start/FEN/a prior successful make, and m
 * belongs to gen(p). Both runtimes parse through gen+make; search, perft and
 * fallback only apply list members (a TT move only changes their ordering).
 * Thus gen proves valid endpoints, side/occupancy, pawn promotion geometry,
 * and the castle origin/transit safety. start/FEN plus rights(from)|rights(to) prove
 * the castle rook exists; normalized EP proves its captured pawn exists.
 * Keep the king-capture prohibition: gen includes attacked king squares.
 * Keep the resulting own-king test: ordinary pins, EP discoveries and castle
 * destination attacks are intentionally filtered only after applying a move. */
int make(const Board *p,Move m,Board *t){
    int from=FROM(m),to=TO(m),prom=PROMO(m),s=p->s;
    int v=p->b[from],target=p->b[to];
    if(abs(target)==6)return 0;
    *t=*p;t->h^=state(p);t->half++;t->e=-1;
    if(abs(v)==1){
        t->half=0;
        if(to==p->e&&!target)put(t,to-s*16,0);
        if(abs(to-from)==32)t->e=from+s*16;
        if(prom)v=s*prom;
    }
    if(target)t->half=0;
    if(abs(v)==6&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        put(t,rook,0);put(t,transit,s*4);
    }
    put(t,from,0);put(t,to,v);t->c&=~(rights(from)|rights(to));t->s=-s;
    if(attacked(t,t->k[s<0],-s))return 0;
    ep(t);t->h^=state(t);
    /* TT context retains the ordered reversible path. A pawn move or capture
     * resets it; repeated boards reached along distinct paths stay distinct. */
    t->r=t->half?((p->r<<1)|(p->r>>63))^t->h:t->h;
    return 1;
}
static void add(Move *moves,int *n,int from,int to,int pawn){
    int promotion=pawn&&((to>>4)==0||(to>>4)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z);
    }
}
/* Forward pseudo generation. King safety and SEE both use shared attackers. */
int gen(const Board *p,Move *moves){
    int s=p->s;
    int n=0;
    for(int from=0;from<128;from++){
        if(from&0x88){from+=7;continue;}
        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;
        if(a==1){
            int to=from+s*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,1);
                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);
            }
        }
        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int d=steps[i];
            for(int to=from+d;!(to&0x88);to+=d){
                int target=p->b[to];
                if(target*s>0||(a==1&&!target&&to!=p->e))break;
                add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
        if(a==6){
            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                if((p->c&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!attacked(p,home+1,-s))add(moves,&n,from,home+2,0);
                if((p->c&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!attacked(p,home-1,-s))add(moves,&n,from,home-2,0);
                }
        }
    }
    return n;
}
void start(Board *p){
    static const int back[8]={4,2,3,5,6,3,2,4};
    Board t={0};t.s=1;t.c=15;t.e=-1;
    for(int f=0;f<8;f++){put(&t,f,back[f]);put(&t,16+f,1);put(&t,96+f,-1);put(&t,112+f,-back[f]);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
#if DEV
int fen(Board *p,const char *s){
    static const char letters[]=" PNBRQK",castles[]="KQkq";
    Board t={0};int rank=7,file=0,kings[2]={0},counts[2]={0};t.s=1;t.e=-1;
    while(*s&&*s!=' '){
        int ch=(unsigned char)*s++;
        if(ch=='/'){if(file!=8||!rank)return 0;rank--;file=0;}
        else if(ch>='1'&&ch<='8'){file+=ch-'0';if(file>8)return 0;}
        else{
            const char *x=strchr(letters,toupper(ch));if(!x||x==letters||file>=8)return 0;
            int v=(int)(x-letters)*(isupper(ch)?1:-1);
            if(++counts[v<0]>16)return 0;
            if(abs(v)==6&&++kings[v<0]>1)return 0;
            put(&t,rank*16+file++,v);
        }
    }
    if(rank||file!=8||kings[0]!=1||kings[1]!=1||*s!=' ')return 0;
    s++;
    if(*s!='w'&&*s!='b')return 0;
    t.s=*s++=='w'?1:-1;
    if(*s!=' ')return 0;
    s++;
    if(*s=='-')s++;
    else while(*s&&*s!=' '){const char *x=strchr(castles,*s++);if(!x)return 0;int b=1<<(x-castles);if(t.c&b)return 0;t.c|=b;}
    if(*s!=' ')return 0;
    s++;
    if(*s=='-')s++;
    else{
        if(!s[0]||!s[1])return 0;
        int f=s[0]-'a',r=s[1]-'1';
        if(f<0||f>7||r!=(t.s>0?5:2))return 0;
        t.e=r*16+f;s+=2;
        if(t.b[t.e]||t.b[t.e-t.s*16]!=-t.s)return 0;
    }
    for(int i=0;i<2;i++){
        if(*s!=' ')return 0;
        char *end;errno=0;long n=strtol(++s,&end,10);
        if(errno||end==s||n<(i?1:0)||n>1000000)return 0;
        if(!i)t.half=(int)n;
        s=end;
    }
    while(*s==' ')s++;
    if(*s)return 0;
    for(int i=0;i<4;i++){int home=i<2?4:116,rook=(i&1)?home-4:home+3,side=i<2?1:-1;if(t.b[home]!=side*6||t.b[rook]!=side*4)t.c&=~(1<<i);}
    ep(&t);t.h^=state(&t);t.r=t.h;*p=t;return 1;
}
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
    ep(&t);return !memcmp(t.bb,p->bb,sizeof t.bb)&&t.e==p->e&&p->h==(t.h^state(&t));
}
#endif


#if DEV
#define COUNT(w,f) (++(w)->f)
#else
#define COUNT(w,f) ((void)0)
#endif

/* A slot is acquired without waiting. Contention is a miss, never a torn
 * key/payload publication. Search workers share slots, not mutable heuristics. */
static uint64_t probe(uint64_t key,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;
    /* All stores have bound 1..3 at bit41 and hence nonzero payload. */
    if(data)e->key=key,e->data=data;
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
    /* Both callers are under depth>0 and pass depth squared. */
    *cell+=(bonus-*cell*bonus/16384);
}
static int piece_index(int p){return p+6;}
static int capture(const Board *p,Move m){return p->b[TO(m)]||
    (abs(p->b[FROM(m)])==1&&TO(m)==p->e);}
static const int material[7]={0,100,320,330,500,900,20000};
#define SEE_INCOMPLETE (-32001)
typedef struct {unsigned visits;int complete;} Exchange;
/* Every recursive capture removes one piece, so <=32 admitted pieces bound
 * depth. A million-visit guard can decline an estimate, never label it losing.
 * SEE's entire tree shares the original search deadline and cancellation. */
static int exchange(Exchange *e,const Board *p,int target){
    if(++e->visits>1000000||atomic_load_explicit(&stopped,memory_order_relaxed)||now()>=deadline){
        e->complete=0;if(now()>=deadline)atomic_store(&stopped,1);return 0;
    }
    int best=0;uint64_t candidates=attackers(p,target,p->s);
    while(candidates){
        int i=__builtin_ctzll(candidates),from=(i&7)+(i&56)*2;candidates&=candidates-1;
        int promotion=abs(p->b[from])==1&&((target>>4)==0||(target>>4)==7);
        for(int z=promotion?2:0;z<=(promotion?5:0);z++){
            /* The target contains the opponent's prior capturer. Shared
             * attackers proves exactly the generated capture geometry; these
             * four promotion choices are precisely gen's. make filters pins
             * and illegal king recaptures. No EP/castle can be a recapture. */
            Board t;if(!make(p,MOVE(from,target,z),&t))continue;
            int gain=material[abs(p->b[target])]+(z?material[z]-100:0)-exchange(e,&t,target);
            if(!e->complete)return 0;if(gain>best)best=gain;
        }
    }
    return best;
}
static int see(Worker *w,const Board *p,Move m){
    COUNT(w,see_calls);Board t;if(!make(p,m,&t))return -MATE;
    Exchange e={0,1};int gain=capture(p,m)?material[abs(p->b[TO(m)])]:0;
    if(!p->b[TO(m)]&&capture(p,m))gain=100;
    gain+=(PROMO(m)?material[PROMO(m)]-100:0)-exchange(&e,&t,TO(m));
    if(e.complete)return gain;COUNT(w,see_incomplete);return SEE_INCOMPLETE;
}
static int search(Worker *w,const Board *p,int depth,int alpha,int beta,int ply,int prior,Move *root,Move excluded,int learning){
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
    int evaluation=p->s*p->v;
    /* Admission: <=32 pieces, each abs(value)<=910. Thus abs(HCE)<=29120.
     * The generated header rejects PLY>879; this stays below mate encoding. */
    if(draw||ply==PLY-1){
        Board q;
        for(int i=0;i<count;i++)if(make(p,moves[i],&q)){
            if(!draw){COUNT(w,ply_aborts);atomic_store(&stopped,1);}
            return 0;
        }
        return check?-MATE+ply:0;
    }
    uint64_t key=p->h^mix(p->r+(unsigned)p->half),data=excluded?0:probe(key,0);
    Move tt=data&131071;
    int score=(int16_t)(data>>17),bound=(data>>41)&3,ttdepth=(data>>33)&255;
    if(bound)COUNT(w,hits);
    if(score>MATE-PLY)score-=ply;
    if(score< -MATE+PLY)score+=ply;
    if(ply&&bound&&ttdepth>=(depth>0?depth:0)&&
       (bound==1||(bound==2&&score>=beta)||(bound==3&&score<=alpha)))return score;
    int singular=0;
    if(!excluded&&ply&&depth>=6&&tt&&ttdepth>=depth-3&&(bound==1||bound==2)&&abs(score)<MATE-PLY){
        int threshold=score-depth*2;COUNT(w,singular_calls);
        int s=search(w,p,(depth-1)/2,threshold-1,threshold,ply,prior,0,tt,0);
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        singular=s<threshold;
    }
    if(depth<=0)COUNT(w,qs);
    int quiet=depth<=0&&!check;
    if(quiet){best=evaluation;if(best>alpha)alpha=best;}
    for(int i=0;i<count;i++){
        Move m=moves[i];int from=FROM(m),to=TO(m),pi=piece_index(p->b[from]);
        scores[i]=m==tt?1000000:capture(p,m)?500000+abs(value(p->b[to],to))*16-abs(value(p->b[from],from)):
            w->history[from][to]+w->continuation[prior][pi]+(int)((m*37u+w->id*19u)%17);
        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;
        if(capture(p,m)||PROMO(m)){int s=see(w,p,m);if(s!=SEE_INCOMPLETE)scores[i]+=s*32;}
    }
    if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
    for(int i=0;i<count;i++){
        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;
        /* The selected prefix is never read again. Remaining order, including
         * equal-score ties, is exactly the original selection sort's. */
        Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];
        if(m==excluded)continue;
        Board q;if(!make(p,m,&q))continue;
        ++legal;
        int from=FROM(m),to=TO(m),tactical=capture(p,m)||PROMO(m),pi=piece_index(q.b[to]);
        if(quiet&&(!tactical||alpha>=beta))continue;
        if(quiet&&!PROMO(m)){int s=see(w,p,m);if(s!=SEE_INCOMPLETE&&s<0)continue;}
        w->keys[w->length++]=q.h;
        int extension=singular&&m==tt,next=depth-1+extension;if(extension){COUNT(w,extensions);}
        if(legal==1||depth<=0)score=-search(w,&q,next,-beta,-alpha,ply+1,pi,0,0,learning);
        else{
            COUNT(w,pvs);
            int reduce=depth>=4&&legal>=4&&!tactical&&!check&&!attacked(&q,q.k[q.s<0],-q.s);
            if(reduce){COUNT(w,corr_uses);reduce=evaluation+w->correction[p->h&1023]/64<alpha+100;}
            score=-search(w,&q,next-reduce,-alpha-1,-alpha,ply+1,pi,0,0,learning);
            if(reduce&&score>alpha)score=-search(w,&q,next,-alpha-1,-alpha,ply+1,pi,0,0,learning);
            if(score>alpha&&score<beta)score=-search(w,&q,next,-beta,-alpha,ply+1,pi,0,0,learning);
        }
        --w->length;
        if(atomic_load_explicit(&stopped,memory_order_relaxed))return 0;
        if(score>best){best=score;bestmove=m;if(root)*root=m;}
        if(score>alpha)alpha=score;
        if(alpha>=beta){
            if(learning&&depth>0&&!tactical){
                int bonus=depth*depth;
                learn(&w->history[from][to],bonus);
                learn(&w->continuation[prior][piece_index(p->b[from])],bonus);
                COUNT(w,hist_updates);COUNT(w,cont_updates);
            }
            break;
        }
    }
    if(!legal)return excluded?old:check?-MATE+ply:0;
    bound=best<=old?3:best>=beta?2:1;
    if(learning&&!excluded&&depth>0&&bound==1&&!check&&bestmove&&!capture(p,bestmove)&&!PROMO(bestmove)&&abs(best)<MATE-PLY){
        int error=best-p->s*p->v;if(error>256)error=256;if(error< -256)error=-256;
        w->correction[p->h&1023]+=error-w->correction[p->h&1023]/64;
        COUNT(w,corr_updates);
    }
    score=best;
    if(score>MATE-PLY)score+=ply;
    if(score< -MATE+PLY)score-=ply;
    data=bestmove|((uint64_t)(uint16_t)score<<17)|((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);
    if(!excluded)probe(key,data);return best;
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
        int score=search(w,p,depth,-MATE,MATE,0,6,&best,0,1);
        if(atomic_load_explicit(&stopped,memory_order_relaxed))break;
        w->best=best;w->score=score;w->depth=depth;
    }
}




static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t command=PTHREAD_COND_INITIALIZER,finished=PTHREAD_COND_INITIALIZER;
static unsigned epoch;
static int pending,ready,quitting;
static Move fallback;

static void text(Move m,char *s){
    if(!m){strcpy(s,"0000");return;}
    s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);
    s[4]="  nbrq"[PROMO(m)];s[4+!!PROMO(m)]=0;
}
static Move first(const Board *b){Move list[MOVES];Board c;int n=gen(b,list);for(int i=0;i<n;i++)if(make(b,list[i],&c))return list[i];return 0;}
static Move parse(const Board *b,const char *s){
    Move list[MOVES];Board c;char name[6];int n=gen(b,list);
    for(int i=0;i<n;i++){text(list[i],name);if(!strcmp(s,name)&&make(b,list[i],&c))return list[i];}return 0;
}
static void result(void){
    flockfile(stdout);
    Worker *w=workers;for(int i=1;i<WORKERS;i++)if(workers[i].depth>w->depth)w=workers+i;
    Move best=w->best?w->best:fallback;char move[6];text(best,move);
#if DEV
    int score=w->score;
    if(abs(score)>=MATE-PLY)printf("info depth %d score mate %d",w->depth,score>0?(MATE-score+1)/2:-(MATE+score+1)/2);
    else printf("info depth %d score cp %d",w->depth,score);
    printf(" nodes %llu",(unsigned long long)atomic_load(&searched));if(best)printf(" pv %s",move);puts("");
#endif
    printf("bestmove %s\n",move);fflush(stdout);funlockfile(stdout);
}
static void *work(void *p){
    Worker *w=p;unsigned seen=0;pthread_mutex_lock(&mutex);ready++;pthread_cond_broadcast(&finished);
    for(;;){
        while(seen==epoch&&!quitting)pthread_cond_wait(&command,&mutex);
        if(quitting)break;
        seen=epoch;pthread_mutex_unlock(&mutex);think(w,&position);pthread_mutex_lock(&mutex);
        if(!--pending){result();pthread_cond_broadcast(&finished);}
    }
    pthread_mutex_unlock(&mutex);return NULL;
}
static void wait(void){atomic_store(&stopped,1);pthread_mutex_lock(&mutex);while(pending)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);}
static void clear(void){for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=table[i].data=0;atomic_flag_clear(&table[i].lock);}}
static void set_position(char *s){
    Board b,c;uint64_t keys[HISTORY];int n=1;char *moves=strstr(s," moves "),*save;
    if(moves){*moves=0;moves+=7;}
    if(!strcmp(s,"startpos"))start(&b);
#if DEV
    else if(!strncmp(s,"fen ",4)){if(!fen(&b,s+4))return;}
#endif
    else return;
    keys[0]=b.h;
    if(moves)for(char *t=strtok_r(moves," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        Move m=parse(&b,t);if(!m||n==HISTORY||!make(&b,m,&c))return;b=c;keys[n++]=b.h;
    }
    position=b;game_length=n;memcpy(game_keys,keys,n*sizeof *keys);
}
static uint64_t number(const char *s){
    uint64_t n=0;if(!s||!*s)return 0;
    for(;*s;s++){unsigned d=(unsigned)(*s-'0');if(d>9||n>((uint64_t)LLONG_MAX-d)/10)return 0;n=n*10+d;}return n;
}
static int read_line(char *s){
    int c,n=0,bad=0;
    while((c=getchar())!=EOF&&c!='\n'){if(!c||n==32767)bad=1;else s[n++]=c;}
    s[n]=0;return c==EOF&&!n?-1:!bad;
}
static void go(char *s){
    wait();
#if DEV
    deadline=UINT64_MAX;
#endif
#if DEV
    limit=0;max_depth=PLY-2;atomic_store(&searched,0);
#endif
#if DEV
    uint64_t clock=0,inc=0,budget=0;int present=0,infinite=0;char *save;
#else
    uint64_t clock=0,inc=0,budget=0;int present=0;char *save;
#endif
    for(char *t=strtok_r(s," \t",&save);t;t=strtok_r(NULL," \t",&save)){
        if(!strcmp(t,"wtime")||!strcmp(t,"btime")||!strcmp(t,"winc")||!strcmp(t,"binc")){int side=*t=='w'?1:-1;uint64_t n=number(strtok_r(NULL," \t",&save));if(side==position.s){if(t[1]=='t'){clock=n;present=1;}else inc=n;}}
#if DEV
        else if(!strcmp(t,"infinite"))infinite=1;
        else if(!strcmp(t,"depth")){uint64_t n=number(strtok_r(NULL," \t",&save));if(n&&n<PLY-1)max_depth=n;}
        else if(!strcmp(t,"nodes"))limit=number(strtok_r(NULL," \t",&save));
        else if(!strcmp(t,"movetime")){budget=number(strtok_r(NULL," \t",&save));if(!budget)budget=1;}
#endif
    }
#if DEV
    if(!infinite){if(!budget&&present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}if(budget)deadline=now()+(budget>86400000?86400000:budget);}
#else
    if(present){budget=clock/30+(inc>86400000?86400000:inc)*3/4;if(budget>clock/5)budget=clock/5;if(!budget)budget=1;}
    else budget=1000;
    deadline=now()+(budget>86400000?86400000:budget);
#endif
    fallback=first(&position);atomic_store(&stopped,0);
    for(int i=0;i<WORKERS;i++){workers[i].depth=workers[i].score=0;workers[i].best=0;workers[i].nodes=0;}
    pthread_mutex_lock(&mutex);pending=WORKERS;epoch++;pthread_cond_broadcast(&command);pthread_mutex_unlock(&mutex);
}
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
    printf("{\"workers\":%d,\"total_threads\":%d,\"nodes\":%llu,\"completed_depth\":%d,\"pvs\":%llu,\"qs\":%llu,\"tt_hits\":%llu,\"history_updates\":%llu,\"continuation_updates\":%llu,\"correction_updates\":%llu,\"correction_uses\":%llu,\"ply_aborts\":%llu}\n",WORKERS,WORKERS+1,(unsigned long long)atomic_load(&searched),depth,(unsigned long long)pvs,(unsigned long long)qs,(unsigned long long)hits,(unsigned long long)hist,(unsigned long long)cont,(unsigned long long)corr,(unsigned long long)uses,(unsigned long long)aborts);fflush(stdout);
}
#endif
int main(void){
    pthread_t threads[WORKERS];int created=0,status=0;char line[32768];
    table=calloc((size_t)1<<TT_BITS,sizeof *table);if(!table)return 2;clear();start(&position);game_keys[0]=position.h;game_length=1;
    for(;created<WORKERS;created++){workers[created].id=created;if(pthread_create(threads+created,NULL,work,workers+created)){status=2;goto shutdown;}}
    pthread_mutex_lock(&mutex);while(ready<WORKERS)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);
    for(;;){
        int status=read_line(line);if(status<0)break;if(!status)continue;
        size_t n=strlen(line);
        while(n&&(line[n-1]=='\n'||line[n-1]=='\r'||line[n-1]==' '||line[n-1]=='\t'))line[--n]=0;
        if(!strcmp(line,"uci")){
#if DEV
            puts("id name Rove4k B\nuciok");
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
