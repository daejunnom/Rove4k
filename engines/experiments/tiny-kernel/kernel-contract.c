/* Explicitly compiled contract fixture; never part of a submitted engine. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
static void observe(const void *,unsigned,int,int);
#define K_OBSERVE(w,m,s,r) observe(w,m,s,r)
#define main engine_main
#include ENGINE_SOURCE
#undef main

static uint64_t checked;
static void contract_text(Move m,char s[6]){
    s[0]='a'+(FROM(m)&7);s[1]='1'+(FROM(m)>>4);
    s[2]='a'+(TO(m)&7);s[3]='1'+(TO(m)>>4);
    s[4]=PROMO(m)?"  nbrq"[PROMO(m)]:0;s[5]=0;
}
static int reference_attack(const Board *p,int tx,int ty,int side){
    for(int y=0;y<8;y++)for(int x=0;x<8;x++){
        int v=p->b[x+16*y],a=abs(v),dx=tx-x,dy=ty-y;
        if(v*side<=0)continue;
        if(a==1&&dy==side&&abs(dx)==1)return 1;
        if(a==2&&abs(dx)*abs(dy)==2)return 1;
        if(a==6&&(dx||dy)&&abs(dx)<=1&&abs(dy)<=1)return 1;
        if(a<3||a>5||(!dx&&!dy))continue;
        int diagonal=abs(dx)==abs(dy),straight=!dx||!dy;
        if(!((a==3&&diagonal)||(a==4&&straight)||(a==5&&(diagonal||straight))))continue;
        int sx=(dx>0)-(dx<0),sy=(dy>0)-(dy<0),px=x+sx,py=y+sy;
        for(;px!=tx||py!=ty;px+=sx,py+=sy)if(p->b[px+16*py])break;
        if(px==tx&&py==ty)return 1;
    }return 0;
}
static void valid(const Board *p){assert(verify_board(p));checked++;}
static void snapshot(const Board *p){
    static const char letters[]=" PNBRQK";valid(p);printf("{\"cells\":\"");
    for(int y=0;y<8;y++)for(int x=0;x<8;x++){
        int v=p->b[x+16*y];putchar(v?(v<0?letters[-v]+'a'-'A':letters[v]):'.');
    }
    printf("\",\"side\":%d,\"castle\":%d,\"ep\":%d,\"kings\":[%d,%d],\"half\":%d,\"v\":%d,\"h\":\"%016llx\",\"r\":\"%016llx\",\"dead\":%d}",
        p->s<0,p->c,p->e,p->k[0],p->k[1],p->half,p->v,(unsigned long long)p->h,(unsigned long long)p->r,dead(p));
}
static void report(const Board *p){
    printf("{\"state\":");snapshot(p);printf(",\"attacks\":\"");
    for(int y=0;y<8;y++)for(int x=0;x<8;x++)for(int c=0;c<2;c++){
        int a=attacked(p,x+16*y,c?-1:1);assert(a==reference_attack(p,x,y,c?-1:1));putchar('0'+a);
    }
    printf("\",\"children\":[");Move moves[MOVES];int n=gen(p,moves),emitted=0;
    for(int i=0;i<n;i++){
        Board q,before=*p;if(!make(p,moves[i],&q))continue;char name[6];contract_text(moves[i],name);
        assert(!memcmp(p,&before,sizeof before));
        assert(q.r==(q.half?((p->r<<1)|(p->r>>63))^q.h:q.h));
        printf("%s{\"move\":\"%s\",\"state\":",emitted++?",":"",name);snapshot(&q);putchar('}');
    }puts("]}");
}
static uint64_t contract_perft(const Board *p,int depth){
    valid(p);if(!depth)return 1;Move moves[MOVES];int n=gen(p,moves);uint64_t total=0;
    for(int i=0;i<n;i++){
        Board q,before=*p;if(make(p,moves[i],&q))total+=contract_perft(&q,depth-1);
        assert(!memcmp(p,&before,sizeof before));
    }return total;
}

#if KERNEL
static struct {
    int enabled,length,count,last,stop_first,prior,live_changed;
    int ranks[131072],stages[131072],seen[131072],piece[131072];
    Move moves[MOVES];
} observation;
static uint64_t observations,root_runs;
static void observe(const void *ptr,unsigned m,int stage,int rank){
    const Worker *w=ptr;if(!observation.enabled||w->length!=observation.length)return;
    assert(m<131072&&observation.stages[m]);
    assert(stage==observation.stages[m]&&rank==observation.ranks[m]);
    int live=w->history[FROM(m)][TO(m)]+w->continuation[observation.prior][observation.piece[m]]+(int)((m*37u+w->id*19u)%17);
    observation.live_changed+=live!=rank;
    assert(stage>=observation.last&&!observation.seen[m]++);
    observation.last=stage;assert(observation.count<MOVES);
    observation.moves[observation.count++]=m;observations++;
    if(observation.stop_first)atomic_store(&stopped,1);
}
static void clear_table(void){
    for(unsigned i=0;i<(1u<<TT_BITS);i++){
        atomic_flag_clear(&table[i].lock);table[i].key=table[i].data=0;
    }
}
static void contract_ready(Worker *w,const Board *p){
    w->length=1;w->keys[0]=p->h;w->nodes=0;deadline=UINT64_MAX;
    atomic_store(&stopped,0);atomic_store(&searched,0);limit=0;
}
static int run(Worker *w,const Board *p,int depth,int alpha,int beta,int prior,Move tt,int ply,int full){
    clear_table();contract_ready(w,p);memset(&observation,0,sizeof observation);
    observation.enabled=1;observation.length=1;observation.prior=prior;
    Move list[MOVES];int n=gen(p,list);
    for(int i=0;i<n;i++){
        Move m=list[i];int rank=w->history[FROM(m)][TO(m)]+w->continuation[prior][piece_index(p->b[FROM(m)])]+(int)((m*37u+w->id*19u)%17);
        observation.ranks[m]=rank;observation.piece[m]=piece_index(p->b[FROM(m)]);
        observation.stages[m]=m==tt?1:(capture(p,m)||PROMO(m))?2:rank>=32?3:4;
    }
    if(tt){uint64_t key=p->h^mix(p->r+(unsigned)p->half);assert(probe(key,tt)==tt);}
    Move best=0;int score=kernel(w,p,depth,alpha,beta,ply,prior,&best,K_SEARCH,0,0);
    assert(w->length==1);if(full){assert(!atomic_load(&stopped));assert(observation.count==n);}
    observation.enabled=0;root_runs++;return score;
}
static void selftest(void){
    table=calloc(1u<<TT_BITS,sizeof *table);assert(table);
    Worker *w=calloc(1,sizeof *w),*peer=calloc(1,sizeof *peer);assert(w&&peer);
    Board p,startpos;start(&p);startpos=p;Move list[MOVES],saved[MOVES];
    int n=gen(&p,list);assert(n==20);
    uint64_t before_observations=observations;atomic_store(&stopped,1);
    assert(first(&p));Board q,alias=p;
    char name[6];contract_text(list[0],name);assert(parse(&p,name,&q));assert(parse(&alias,name,&alias));
    assert(!memcmp(&q,&alias,sizeof q));valid(&q);assert(atomic_load(&stopped)==1);
    Board unchanged=p;assert(!parse(&p,"a1a8",&unchanged));assert(!memcmp(&p,&unchanged,sizeof p));
    unchanged=p;assert(!kernel(0,&p,0,0,0,0,0,0,K_MATCH,MOVE(0,0,0),&unchanged));
    assert(!memcmp(&p,&unchanged,sizeof p));
    for(int c=0;c<2;c++)for(int y=0;y<8;y++)for(int x=0;x<8;x++)assert(attacked(&p,x+16*y,c?-1:1)==reference_attack(&p,x,y,c?-1:1));
    assert(gen(&p,list)==20&&observations==before_observations);

    run(w,&p,1,-MATE,MATE,6,0,0,1);memcpy(saved,observation.moves,sizeof saved);
    peer->id=1;run(peer,&p,1,-MATE,MATE,6,0,0,1);
    assert(memcmp(saved,observation.moves,n*sizeof *saved));
    int fresh_count=observation.count;

    assert(fen(&p,"r1r4k/1P6/8/3pP3/8/8/8/7K w - d6 0 1"));
    n=gen(&p,list);Move tt=0;for(int i=0;i<n;i++)if(!capture(&p,list[i])&&!PROMO(list[i])){tt=list[i];break;}
    assert(tt);memset(w,0,sizeof *w);run(w,&p,1,-MATE,MATE,6,tt,0,1);
    int stage_counts[5]={0};for(int i=0;i<n;i++)stage_counts[observation.stages[list[i]]]++;
    assert(stage_counts[1]==1&&stage_counts[2]>=13&&stage_counts[4]);

    p=startpos;memset(w,0,sizeof *w);run(w,&p,4,-MATE,MATE,6,0,0,1);
    assert(w->pvs&&w->qs&&w->hits&&w->hist_updates&&w->cont_updates&&w->corr_updates&&w->corr_uses);
    assert(observation.live_changed);int snapshot_live_changes=observation.live_changed;
    uint64_t snapshot_updates=w->hist_updates,pvs=w->pvs,qs=w->qs,hits=w->hits,corr_updates=w->corr_updates,corr_uses=w->corr_uses;

    assert(fen(&p,"7k/8/8/8/8/8/P7/K7 w - - 0 1"));memset(w,0,sizeof *w);
    run(w,&p,1,-MATE,MATE,6,0,0,1);Move trained=observation.moves[0];
    assert(observation.stages[trained]==4);memset(w,0,sizeof *w);
    run(w,&p,6,-MATE,-MATE+1,6,0,0,0);
    assert(!atomic_load(&stopped)&&observation.count==1&&observation.moves[0]==trained);
    int from=FROM(trained),to=TO(trained),pi=piece_index(p.b[from]);
    int history=w->history[from][to],continuation=w->continuation[6][pi];
    assert(history>=36&&continuation>=36&&w->hist_updates&&w->cont_updates);
    Move alternative=0;n=gen(&p,list);
    for(int i=0;i<n;i++)if(list[i]!=trained&&piece_index(p.b[FROM(list[i])])==pi&&!capture(&p,list[i])&&!PROMO(list[i])&&!w->history[FROM(list[i])][TO(list[i])]){alternative=list[i];break;}
    assert(alternative);
    run(w,&p,1,-MATE,MATE,6,0,0,1);
    assert(observation.stages[trained]==3&&observation.stages[alternative]==3);
    assert(observation.ranks[alternative]>=32);
    int alternative_rank=observation.ranks[alternative];
    assert(!w->continuation[5][pi]);run(w,&p,1,-MATE,MATE,5,0,0,1);
    assert(observation.stages[trained]==3&&observation.ranks[trained]>=32);

    contract_ready(w,&p);clear_table();memset(&observation,0,sizeof observation);
    observation.enabled=1;observation.length=1;observation.stop_first=1;observation.prior=6;
    n=gen(&p,list);for(int i=0;i<n;i++){
        Move m=list[i];observation.ranks[m]=w->history[FROM(m)][TO(m)]+w->continuation[6][piece_index(p.b[FROM(m)])]+(int)((m*37u+w->id*19u)%17);observation.piece[m]=piece_index(p.b[FROM(m)]);
        observation.stages[m]=(capture(&p,m)||PROMO(m))?2:observation.ranks[m]>=32?3:4;
    }
    Move best=0;assert(kernel(w,&p,3,-MATE,MATE,0,6,&best,K_SEARCH,0,0)==0);
    assert(atomic_load(&stopped)&&w->length==1&&observation.count==1);observation.enabled=0;
    uint64_t nodes=w->nodes;best=0;assert(kernel(w,&p,3,-MATE,MATE,0,6,&best,K_SEARCH,0,0)==0&&w->nodes==nodes);

    assert(fen(&p,"7k/6Q1/6K1/8/8/8/8/8 b - - 100 1"));contract_ready(w,&p);
    assert(kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0)==-MATE&&!atomic_load(&stopped));
    assert(fen(&p,"7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"));contract_ready(w,&p);
    assert(kernel(w,&p,0,-MATE,MATE,0,6,0,K_SEARCH,0,0)==0&&!atomic_load(&stopped));
    assert(fen(&p,"7k/8/8/8/8/8/8/K7 w - - 0 1"));contract_ready(w,&p);
    assert(kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0)==0&&!atomic_load(&stopped));
    p=startpos;p.half=100;contract_ready(w,&p);assert(kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0)==0&&!atomic_load(&stopped));
    p=startpos;p.half=8;contract_ready(w,&p);w->length=5;for(int i=0;i<5;i++)w->keys[i]=p.h;
    assert(kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0)==0&&w->length==5&&!atomic_load(&stopped));
    contract_ready(w,&p);assert(kernel(w,&p,1,-MATE,MATE,PLY-1,6,0,K_SEARCH,0,0)==0&&atomic_load(&stopped)&&w->length==1);
    assert(fen(&p,"7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"));contract_ready(w,&p);
    assert(kernel(w,&p,1,-MATE,MATE,PLY-1,6,0,K_SEARCH,0,0)==-MATE+PLY-1&&!atomic_load(&stopped));
    assert(fen(&p,"r6k/8/8/8/8/8/7P/K7 w - - 0 1"));memset(w,0,sizeof *w);
    run(w,&p,0,-MATE,MATE,6,0,0,1);assert(observation.count==2&&w->nodes>=3);
    assert(fen(&p,"7k/8/8/3pP3/8/8/8/7K w - d6 0 1"));memset(w,0,sizeof *w);
    run(w,&p,1,-MATE,MATE,6,0,0,1);
    Move epbest=probe(p.h^mix(p.r+(unsigned)p.half),0)&131071;
    assert(TO(epbest)==(unsigned)p.e&&!p.b[TO(epbest)]&&abs(p.b[FROM(epbest)])==1&&!w->corr_updates);
    assert(fen(&p,"7k/8/8/8/8/8/8/KR6 w - - 0 1"));memset(w,0,sizeof *w);contract_ready(w,&p);clear_table();
    int fresh_score=kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0);assert(fresh_score>0);
    uint64_t fresh_key=p.h^mix(p.r);p.half=99;uint64_t late_key=p.h^mix(p.r+99);
    assert(fresh_key!=late_key&&!probe(late_key,0));contract_ready(w,&p);
    int late_score=kernel(w,&p,1,-MATE,MATE,0,6,0,K_SEARCH,0,0);assert(!late_score&&!atomic_load(&stopped));
    printf("{\"passed\":true,\"checks\":{\"utility_isolation\":true,\"stage_partition\":true,\"cached_rank\":true,\"learned_order\":true,\"fresh_order\":true,\"stop\":true,\"draw\":true,\"ply\":true,\"positive_algorithms\":true,\"ep_correction_exclusion\":true,\"halfmove_context\":true},\"root_runs\":%llu,\"root_legal_observations\":%llu,\"fresh_root_moves\":%d,\"tactical_fixture_moves\":%d,\"snapshot_descendant_updates\":%llu,\"snapshot_changed_live_ranks\":%d,\"learned_history\":%d,\"learned_continuation\":%d,\"other_quiet_continuation_rank\":%d,\"pvs\":%llu,\"qs\":%llu,\"tt_hits\":%llu,\"correction_updates\":%llu,\"correction_uses\":%llu,\"fresh_score\":%d,\"half99_score\":%d}\n",
        (unsigned long long)root_runs,(unsigned long long)observations,fresh_count,stage_counts[2],(unsigned long long)snapshot_updates,snapshot_live_changes,history,continuation,alternative_rank,
        (unsigned long long)pvs,(unsigned long long)qs,(unsigned long long)hits,(unsigned long long)corr_updates,(unsigned long long)corr_uses,fresh_score,late_score);
    free(w);free(peer);free(table);table=0;
}
#else
static void observe(const void *w,unsigned m,int s,int r){(void)w;(void)m;(void)s;(void)r;}
#endif

int main(void){
    Board p;start(&p);char line[4096];
    while(fgets(line,sizeof line,stdin)){
        line[strcspn(line,"\r\n")]=0;
        if(!strcmp(line,"start")){start(&p);printf("{\"ok\":true,\"state\":");snapshot(&p);puts("}");}
        else if(!strncmp(line,"fen ",4)){
            Board before=p;int ok=fen(&p,line+4);if(!ok)assert(!memcmp(&p,&before,sizeof p));
            printf("{\"ok\":%s,\"state\":",ok?"true":"false");snapshot(&p);puts("}");
        }else if(!strcmp(line,"report"))report(&p);
        else if(!strncmp(line,"play ",5)){
            Move moves[MOVES];int n=gen(&p,moves),ok=0;char name[6];
            for(int i=0;i<n;i++){contract_text(moves[i],name);if(!strcmp(name,line+5)){Board q;if(make(&p,moves[i],&q)){p=q;ok=1;}break;}}
            printf("{\"ok\":%s,\"state\":",ok?"true":"false");snapshot(&p);puts("}");
        }else if(!strncmp(line,"perft ",6)){
            int d=atoi(line+6);assert(d>=0&&d<=3);checked=0;uint64_t nodes=contract_perft(&p,d);
            printf("{\"nodes\":%llu,\"checked\":%llu}\n",(unsigned long long)nodes,(unsigned long long)checked);
        }else if(!strcmp(line,"selftest")){
#if KERNEL
            selftest();
#else
            puts("{\"control_only\":true}");
#endif
        }else if(!strcmp(line,"quit"))return 0;
        else abort();
        fflush(stdout);
    }return 0;
}
