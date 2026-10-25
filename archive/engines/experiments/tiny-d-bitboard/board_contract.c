/* Standalone DEV contract. Link board.c + hq.c with the host C library;
 * production runtime is validated separately. The independent Python oracle
 * checks legal sets, perft, state transitions and all observable fields. */
#include "tiny.h"
#include "hq.h"
#include <stdio.h>
#define CHECK(x) do{if(!(x)){printf("FAIL line %d: %s\n",__LINE__,#x);return 0;}}while(0)
int tiny_errno;
static uint64_t positions,moves_checked;
static uint64_t independent_mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);
}
static int recompute(const Board *p){
    uint64_t h=independent_mix(2048+p->c)^(p->s?independent_mix(2064):0)^
        (p->e<0?0:independent_mix(2065+(p->e%8)));int score=0;
    const int material[6]={100,320,330,500,900,0};
    for(int q=0;q<64;q++)for(int c=0;c<2;c++)if(p->color[c]&(UINT64_C(1)<<q)){
        int kind=-1;for(int k=0;k<6;k++)if(p->pieces[k]&(UINT64_C(1)<<q)){if(kind>=0)return 0;kind=k;}
        if(kind<0)return 0;
        int r=q/8,f=q%8,a=c?7-r:r,center=7-abs(2*f-7)-abs(2*r-7);
        int v=material[kind]+(kind==0?a*7:kind==3?a*2:0)+center*(kind==1?9:kind==2?5:kind==5?-3:kind==0||kind==4?2:0);
        score+=c?-v:v;h^=independent_mix(q+(kind+6*c)*64);
    }
    return score==p->v&&h==p->h&&verify_board(p);
}
static uint64_t tree(const Board *p,int depth){
    if(!recompute(p))return UINT64_MAX;
    positions++;if(!depth)return 1;
    Move list[MOVES];int n=gen(p,list);uint64_t count=0;
    for(int i=0;i<n;i++){
        Board t;Move m=list[i];if(!make(p,m,&t))continue;moves_checked++;
        if(!recompute(&t)||t.s!=(p->s^1)||t.c&~p->c)return UINT64_MAX;
        int irreversible=KIND(m)==0||CAP(m),half=irreversible?0:p->half+1;
        uint64_t context=half?((p->r<<1)|(p->r>>63))^t.h:t.h;
        if(t.half!=half||t.r!=context)return UINT64_MAX;
        uint64_t v=tree(&t,depth-1);if(v==UINT64_MAX)return v;count+=v;
    }
    return count;
}
static int named(const char *fen_text,int depth,uint64_t expected){
    Board p;CHECK(fen(&p,fen_text));CHECK(recompute(&p));CHECK(tree(&p,depth)==expected);return 1;
}
static int transition(const char *fen_text,int from,int to,int promo,int expected_cap,int expected_piece){
    Board p;CHECK(fen(&p,fen_text));CHECK(recompute(&p));Move moves[MOVES];int n=gen(&p,moves),found=0;
    for(int i=0;i<n;i++)if(FROM(moves[i])==from&&TO(moves[i])==to&&PROMO(moves[i])==promo){
        Board t;CHECK(make(&p,moves[i],&t));CHECK(CAP(moves[i])==expected_cap);
        CHECK(t.pieces[expected_piece]&(UINT64_C(1)<<to));CHECK(recompute(&t));found++;
    }
    CHECK(found==1);return 1;
}
static uint64_t scalar(uint64_t o,int sq,int kind){
    const int df[8]={1,-1,0,0,1,-1,1,-1},dr[8]={0,0,1,-1,1,1,-1,-1};uint64_t result=0;
    for(int d=kind==2?4:0;d<(kind==3?4:8);d++)for(int f=sq%8+df[d],r=sq/8+dr[d];f>=0&&f<8&&r>=0&&r<8;f+=df[d],r+=dr[d]){
        uint64_t bit=UINT64_C(1)<<(r*8+f);result|=bit;if(o&bit)break;
    }
    return result;
}
static int sliders(void){
    uint64_t r=UINT64_C(0x920a01bcd872189f);unsigned count=0;
    for(int sq=0;sq<64;sq++)for(int k=2;k<5;k++)for(int i=0;i<1024;i++){
        r=independent_mix(r);uint64_t occupancies[4]={r,~r,r|(UINT64_C(1)<<sq),r&~(UINT64_C(1)<<sq)};
        for(int j=0;j<4;j++){CHECK(d_sliding(occupancies[j],(unsigned)sq,(unsigned)k)==scalar(occupancies[j],sq,k));count++;}
    }
    printf("sliders %u\n",count);return 1;
}
static int leaps(void){
    unsigned count=0;
    for(int kind=0;kind<6;kind++)if(kind==0||kind==1||kind==5)
        for(int c=0;c<2;c++)for(int from=0;from<64;from++)for(int to=0;to<64;to++){
            Board p={0};p.color[c]=p.pieces[kind]=UINT64_C(1)<<from;
            int df=abs(to%8-from%8),dr=to/8-from/8,ar=abs(dr);
            int expected=kind==0?df==1&&dr==(c?-1:1):kind==1?(df==1&&ar==2)||(df==2&&ar==1):(df||ar)&&df<=1&&ar<=1;
            CHECK(attacked(&p,to,c)==expected);count++;
        }
    printf("leapers %u\n",count);return 1;
}
static int run(void){
    CHECK(sliders());CHECK(leaps());Board p;start(&p);CHECK(recompute(&p));CHECK(p.s==0&&p.c==15&&p.e==-1&&p.v==0&&p.r==p.h);
    CHECK(tree(&p,4)==197281);
    CHECK(named("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",3,97862));
    CHECK(named("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",4,43238));
    CHECK(transition("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",36,43,0,1,0));
    CHECK(transition("4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",28,19,0,1,0));
    CHECK(transition("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",4,6,0,0,5));
    CHECK(transition("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",60,58,0,0,5));
    for(int z=2;z<=5;z++){
        CHECK(transition("4k2r/6P1/8/8/8/8/8/4K3 w - - 0 1",54,63,z,4,z-1));
        CHECK(transition("4k3/8/8/8/8/8/1p6/R3K3 b - - 0 1",9,0,z,4,z-1));
    }
    Board a,b;CHECK(fen(&a,"k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"));
    CHECK(fen(&b,"k3r3/8/8/3pP3/8/8/8/4K3 w - - 0 1"));CHECK(a.e==-1&&a.h==b.h);
    CHECK(fen(&a,"8/8/8/r4pPK/8/8/8/k7 w - f6 0 1"));CHECK(a.e==-1);
    CHECK(fen(&a,"k7/8/2b5/3pP3/4K3/8/8/8 w - d6 0 1"));CHECK(a.e==-1);
    CHECK(fen(&a,"k7/8/8/3pP3/4K3/8/8/8 w - d6 0 1"));CHECK(a.e==43);
    CHECK(fen(&a,"k3r3/8/8/2PpP3/8/8/8/4K3 w - d6 0 1"));CHECK(a.e==43);
    CHECK(fen(&a,"4k3/8/8/3p4/8/8/8/4K3 w - d6 0 1"));CHECK(a.e==-1);
    CHECK(fen(&a,"4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"));CHECK(a.e==43);
    CHECK(fen(&a,"4k3/8/8/8/8/8/8/4K3 w KQkq - 0 1"));CHECK(!a.c&&dead(&a));
    CHECK(fen(&a,"4k3/8/8/8/8/8/8/1NN1K3 w - - 0 1"));CHECK(!dead(&a));
    CHECK(fen(&a,"4k3/8/8/8/8/8/5B2/2B1K3 w - - 0 1"));CHECK(dead(&a));
    CHECK(fen(&a,"4k3/8/8/8/8/8/4B3/2B1K3 w - - 0 1"));CHECK(!dead(&a));
    a.e=0;CHECK(!verify_board(&a));a.e=63;CHECK(!verify_board(&a));
    printf("PASS positions %llu legalmoves %llu Board %zu\n",(unsigned long long)positions,(unsigned long long)moves_checked,sizeof(Board));return 1;
}
int main(void){return run()?0:1;}
