/* Include the exact producer input, so tests call actual shipping consumers. */
#define main tiny_e_engine_main
#include TINY_E_SOURCE
#undef main
#include <assert.h>

static uint32_t rng=0xe2026102;
static uint32_t random32(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static int center64(int q){int f=q%8,r=q/8;return (f<4?f:7-f)+(r<4?r:7-r);}
static int oracle_white(const Board *p){
    const int material[]={0,100,320,330,500,900,0},central[]={0,3,8,5,2,1,-3};
    int files[2][8]={{0}},bishops[2]={0},answer=10*p->s;
    for(int n=0;n<64;n++){
        int pc=p->b[(n/8)*16+n%8],a=abs(pc),black=pc<0,sign=black?-1:1;
        if(!pc)continue;
        answer+=sign*(material[a]+central[a]*center64(n));
        if(a==1){files[black][n%8]++;answer+=sign*6*((black?7-n/8:n/8)-1);}
        bishops[black]+=a==3;
    }
    for(int black=0;black<2;black++){
        int side=bishops[black]>=2?24:0;
        for(int file=0;file<8;file++){
            int n=files[black][file];if(!n)continue;
            side-=12*(n-1);
            if((file==0||!files[black][file-1])&&(file==7||!files[black][file+1]))side-=8*n;
        }
        answer+=black?-side:side;
    }
    return answer;
}
static int oracle_order(const Board *p,Move m){
    const int material[]={0,100,320,330,500,900,0};
    int f=FROM(m),t=TO(m),a=abs(p->b[f]),victim=abs(p->b[t]),prom=PROMO(m);
    if(a==1&&!victim&&p->e==t)victim=1;
    int answer=2*(center64((t>>4)*8+(t&7))-center64((f>>4)*8+(f&7)));
    if(victim)answer+=16*material[victim]-material[a];
    if(prom)answer+=12*(material[prom]-100);
    if(a==1)answer+=4*((t>>4)-(f>>4))*(p->b[f]<0?-1:1);
    return answer;
}
static int oracle_hce(const Board *p){
    const int material[]={0,100,320,330,500,900,0};int sum=0;
    for(int n=0;n<64;n++){
        int pc=p->b[(n/8)*16+n%8],a=abs(pc);if(!pc)continue;
        int f=n%8,r=n/8,c=7-abs(2*f-7)-abs(2*r-7),advance=pc>0?r:7-r;
        int v=material[a]+advance*(a==1?7:a==4?2:0)+c*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
        sum+=pc>0?v:-v;
    }
    return sum;
}
static uint64_t independent_mix(uint64_t n){
    n+=UINT64_C(0x9e3779b97f4a7c15);n=(n^(n>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    n=(n^(n>>27))*UINT64_C(0x94d049bb133111eb);return n^(n>>31);
}
static void board_contract(const Board *p){
    uint64_t hash=independent_mix(2048+p->c)^(p->s<0?independent_mix(2064):0)^
        (p->e<0?0:independent_mix(2065+(p->e&7)));
    for(int n=0;n<64;n++){
        int q=n/8*16+n%8,v=p->b[q];if(v)hash^=independent_mix((uint64_t)(q+(v+6)*128));
    }
    assert(hash==p->h);
#if DEV
    assert(p->v==oracle_hce(p));assert(verify_board(p));
#else
    (void)oracle_hce;
#endif
    assert(tiny_white(p)==oracle_white(p));
}
static void finish_fixture(Board *p){ep(p);p->h^=state(p);p->r=p->h;board_contract(p);}
static void special_contracts(void){
    Board p={0},q;p.s=1;p.e=83;put(&p,4,6);put(&p,116,-6);put(&p,68,1);put(&p,67,-1);
    finish_fixture(&p);assert(p.e==83);Move capture_ep=MOVE(68,83,0);
    assert(tiny_order(&p,capture_ep)==1502);assert(make(&p,capture_ep,&q));
    assert(q.b[83]==1&&!q.b[67]&&!q.b[68]&&q.half==0);board_contract(&q);
    memset(&p,0,sizeof p);p.s=1;p.e=85;put(&p,71,6);put(&p,116,-6);put(&p,64,-4);put(&p,70,1);put(&p,69,-1);
    finish_fixture(&p);assert(p.e==-1);
    memset(&p,0,sizeof p);p.s=1;p.e=-1;put(&p,4,6);put(&p,116,-6);put(&p,96,1);put(&p,113,-4);finish_fixture(&p);
    for(int prom=2;prom<=5;prom++)for(int target=112;target<=113;target++){
        Move m=MOVE(96,target,prom);assert(parse(&p,target==112?(prom==2?"a7a8n":prom==3?"a7a8b":prom==4?"a7a8r":"a7a8q"):(prom==2?"a7b8n":prom==3?"a7b8b":prom==4?"a7b8r":"a7b8q"))==m);
        assert(tiny_order(&p,m)==oracle_order(&p,m));assert(make(&p,m,&q));assert(q.b[target]==prom&&q.half==0);board_contract(&q);
    }
    for(int side=-1;side<=1;side+=2)for(int queen=0;queen<2;queen++){
        memset(&p,0,sizeof p);p.s=side;p.c=15;p.e=-1;
        put(&p,4,6);put(&p,116,-6);put(&p,0,4);put(&p,7,4);put(&p,112,-4);put(&p,119,-4);finish_fixture(&p);
        int home=side==1?4:116,target=home+(queen?-2:2),rook=home+(queen?-4:3),transit=home+(queen?-1:1);
        assert(make(&p,MOVE(home,target,0),&q));assert(q.b[target]==6*side&&q.b[transit]==4*side&&!q.b[home]&&!q.b[rook]);board_contract(&q);
    }
    memset(&p,0,sizeof p);p.s=1;p.e=-1;put(&p,4,6);put(&p,116,-6);finish_fixture(&p);assert(dead(&p));
    put(&p,2,3);assert(dead(&p));put(&p,1,2);assert(!dead(&p));
}
int main(void){
    uint64_t digest=0;unsigned evaluations=0,orders=0,transitions=0,positive=0,negative=0;
    for(int sample=0;sample<20000;sample++){
        Board p={0};p.s=(sample&1)?1:-1;p.e=-1;
        for(int n=0;n<64;n++){
            int pc=sample<12?((sample<6?1:-1)*(sample%6+1)):(int)(random32()%13)-6;
            p.b[(n/8)*16+n%8]=(int8_t)pc;
        }
        int expected=oracle_white(&p),clamped=expected>20000?20000:expected< -20000?-20000:expected;
        assert(expected==tiny_white(&p));assert(clamped==tiny_raw(&p));evaluations++;
        positive+=expected>20000;negative+=expected< -20000;
        for(int i=0;i<8;i++){
            int f=(int)(random32()%64),t=(int)(random32()%64);f=f/8*16+f%8;t=t/8*16+t%8;
            if(!p.b[f])p.b[f]=p.s;
            int prom=abs(p.b[f])==1?(int)(random32()%5):0;prom=prom?prom+1:0;
            if(abs(p.b[f])==1&&!p.b[t]&&(i&1))p.e=t;else p.e=-1;
            Move m=MOVE(f,t,prom);assert(tiny_order(&p,m)==oracle_order(&p,m));orders++;
        }
    }
    assert(positive&&negative);
    special_contracts();
    for(int game=0;game<40;game++){
        Board p;start(&p);board_contract(&p);
        for(int ply=0;ply<200;ply++){
            Move moves[MOVES],legal[MOVES];Board t;int n=gen(&p,moves),count=0;
            for(int i=0;i<n;i++)if(make(&p,moves[i],&t)){
                board_contract(&t);assert(t.r==(t.half?((p.r<<1)|(p.r>>63))^t.h:t.h));
                legal[count++]=moves[i];transitions++;
            }
            if(!count)break;
            assert(make(&p,legal[random32()%(unsigned)count],&t));p=t;digest^=p.h+(digest<<6)+(digest>>2);
        }
    }
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);clear();
    Board p;start(&p);deadline=UINT64_MAX;atomic_store(&stopped,0);
    Worker w={0};w.keys[0]=p.h;w.length=1;Move best=0;
    int score=search(&w,&p,4,-MATE,MATE,0,0,&best);assert(best&&!atomic_load(&stopped));Move depth4_best=best;
    unsigned history=0,continuation=0,correction=0;
    for(int i=0;i<128;i++)for(int j=0;j<128;j++)history+=w.history[i][j]!=0;
    for(int i=0;i<13;i++)for(int j=0;j<13;j++)continuation+=w.continuation[i][j]!=0;
    for(int i=0;i<1024;i++)correction+=w.correction[i]!=0;
    assert(history&&continuation&&correction);
    uint64_t key=p.h^mix(p.r+(unsigned)p.half);probe(key,1,123);
    assert(probe(key,0,0)==123);assert(probe(key+((uint64_t)1<<TT_BITS),0,0)==0);
    Board q=p;q.half++;assert((q.h^mix(q.r+(unsigned)q.half))!=key);
    q=p;q.r++;assert((q.h^mix(q.r+(unsigned)q.half))!=key);
    clear();memset(&w,0,sizeof w);w.length=5;w.keys[0]=w.keys[2]=w.keys[4]=p.h;p.half=4;
    atomic_store(&stopped,0);assert(search(&w,&p,1,-MATE,MATE,0,0,&best)==0);assert(!atomic_load(&stopped));
    w.length=3;w.keys[0]=w.keys[2]=p.h;assert(search(&w,&p,1,-MATE,MATE,0,0,&best)!=0);
    p.half=100;assert(search(&w,&p,1,-MATE,MATE,0,0,&best)==0);
    memset(&p,0,sizeof p);p.s=-1;p.e=-1;p.half=100;put(&p,119,-6);put(&p,102,5);put(&p,85,6);finish_fixture(&p);
    w.length=1;w.keys[0]=p.h;assert(search(&w,&p,1,-MATE,MATE,0,0,&best)==-MATE);
    start(&p);w.length=1;w.keys[0]=p.h;atomic_store(&stopped,0);
    assert(search(&w,&p,1,-MATE,MATE,PLY-1,0,&best)==0);assert(atomic_load(&stopped));
    free(table);
    printf("{\"board_bytes\":%zu,\"evaluations\":%u,\"orders\":%u,\"transitions\":%u,\"transition_digest\":\"%016llx\",\"depth4_score\":%d,\"depth4_best\":%u,\"history_cells\":%u,\"continuation_cells\":%u,\"correction_cells\":%u,\"clamp_positive\":%u,\"clamp_negative\":%u,\"tt_context_abort\":true}\n",sizeof(Board),evaluations,orders,transitions,(unsigned long long)digest,score,depth4_best,history,continuation,correction,positive,negative);
    return 0;
}
