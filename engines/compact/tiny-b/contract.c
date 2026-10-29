/* Appended to the actual generated DEV translation unit by check.py.
 * No substitute board/SEE/search is linked. */
#include <assert.h>
#include <inttypes.h>

static void load(Board *p,const char *s){assert(fen(p,s));assert(verify_board(p));}
static Move move(const Board *p,const char *s){Move m=parse(p,s);assert(m);return m;}
static Worker *prepare(const Board *p){
    clear();memset(workers,0,sizeof workers);atomic_store(&stopped,0);atomic_store(&searched,0);
    deadline=now()+30000;limit=0;max_depth=10;
    Worker *w=workers;w->keys[0]=p->h;w->length=1;return w;
}
static uint64_t key(const Board *p){return p->h^mix(p->r+(unsigned)p->half);}
static int reference(const Board *p,int sq,int side){
    for(int f=0;f<128;f++)if(!(f&0x88)&&p->b[f]*side>0){
        int a=abs(p->b[f]);
        if(a==1){if(sq==f+side*16-1||sq==f+side*16+1)return 1;continue;}
        int first=a==2?0:a==3?12:8,last=a==2?8:a==4?12:16;
        for(int i=first;i<last;i++)for(int q=f+steps[i];!(q&0x88);q+=steps[i]){
            if(q==sq)return 1;if(p->b[q]||a==2||a==6)break;
        }
    }
    return 0;
}
static void test_bitboards(void){
    int bound=0;for(int v=-6;v<=6;v++)for(int q=0;q<128;q++)if(!(q&0x88)&&abs(value(v,q))>bound)bound=abs(value(v,q));
    assert(bound==910&&32*bound<=MATE-PLY-1);
    Board p;start(&p);uint64_t seed=UINT64_C(0x20261020);unsigned transitions=0,queries=0;
    for(int n=0;n<400;n++){
        assert(verify_board(&p));
        for(int q=0;q<128;q++)if(!(q&0x88))for(int s=-1;s<=1;s+=2){assert(attacked(&p,q,s)==reference(&p,q,s));queries++;}
        Move list[MOVES],legal[MOVES];Board child;int count=gen(&p,list),length=0;
        for(int i=0;i<count;i++)if(make(&p,list[i],&child)){assert(verify_board(&child));legal[length++]=list[i];transitions++;}
        if(!length||n%73==72){start(&p);continue;}
        seed=mix(seed);assert(make(&p,legal[seed%length],&child));p=child;
    }
    printf("incremental bitboards/shared attackers: %u legal children, %u differential queries: pass\n",transitions,queries);
}
static void test_see(void){
    static const struct{const char *fen,*move;int score;}cases[]={
        {"7k/8/8/8/8/8/p7/R3K3 w - - 0 1","a1a2",100},
        {"3r3k/8/8/3p4/8/8/8/3Q3K w - - 0 1","d1d5",-800},
        {"4k3/4p3/3p4/8/1B6/8/8/4R2K w - - 0 1","b4d6",100},
        {"4k3/3p4/8/8/8/8/8/3Q3K w - - 0 1","d1d7",-800},
        {"4k3/3p4/8/8/6B1/8/8/3Q3K w - - 0 1","d1d7",100},
        {"7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1","e5d6",100},
        {"1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7a8q",-100},
        {"1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8q",1300},
        {"1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8n",720},
        {"3r3k/8/8/3p4/3R4/8/8/3Q3K w - - 0 1","d4d5",100},
    };
    for(unsigned i=0;i<sizeof cases/sizeof *cases;i++){
        Board p;load(&p,cases[i].fen);Worker *w=prepare(&p);int score=see(w,&p,move(&p,cases[i].move));
        if(score!=cases[i].score)fprintf(stderr,"SEE %s got %d expected %d\n",cases[i].move,score,cases[i].score);
        assert(score==cases[i].score&&w->see_calls==1&&w->see_incomplete==0&&verify_board(&p));
    }
    Board p;load(&p,"k7/8/8/4KPpr/8/8/8/8 w - g6 0 1");assert(!parse(&p,"f5g6"));
    /* This EP is removed by canonicalization. It is not a gen member and
     * therefore must not be supplied to the generated-move-only make/SEE API. */
    Move list[MOVES];int n=gen(&p,list);for(int i=0;i<n;i++)assert(list[i]!=MOVE(69,86,0));
    Worker *w=prepare(&p);
    load(&p,"4r2k/8/8/8/8/3p4/4B3/4K3 w - - 0 1");assert(!parse(&p,"e2d3"));
    w=prepare(&p);assert(see(w,&p,MOVE(20,35,0))==-MATE);
    load(&p,"7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1");w=prepare(&p);Move m=move(&p,"e5d6");
    atomic_store(&stopped,1);assert(see(w,&p,m)==SEE_INCOMPLETE&&w->see_incomplete==1);
    atomic_store(&stopped,0);deadline=now()-1;uint64_t original=deadline;
    assert(see(w,&p,m)==SEE_INCOMPLETE&&atomic_load(&stopped)&&deadline==original&&w->see_incomplete==2);
    puts("legal SEE: ten pins/king/EP/promotions/optional-capture cases, two illegal controls, stop/original-deadline expiry: pass");
}
static void same_learning(const Worker *w,const Worker *saved){
    assert(!memcmp(w->history,saved->history,sizeof w->history));
    assert(!memcmp(w->continuation,saved->continuation,sizeof w->continuation));
    assert(!memcmp(w->correction,saved->correction,sizeof w->correction));
}
static void test_singular(void){
    Board p,prior;load(&prior,"7k/6p1/8/8/8/8/PK6/8 b - - 0 1");Move last=move(&prior,"h8h7");assert(make(&prior,last,&p));
    Worker *w=prepare(&p);Move best=0;int prime=search(w,&p,3,-MATE,MATE,1,last,&best,0,1);
    assert(!atomic_load(&stopped));uint64_t data=probe(key(&p),0);Move candidate=data&131071;
    assert(candidate&&((data>>33)&255)>=3&&((data>>41)&3)==1);
    uint64_t before=w->singular_calls;(void)search(w,&p,6,-MATE,MATE,1,last,&best,0,1);
    assert(!atomic_load(&stopped)&&w->singular_calls>before);
    printf("actual depth-3 exact TT candidate qualifies depth-6 singular probes=%" PRIu64 ": pass\n",w->singular_calls-before);

    w=prepare(&p);prime=search(w,&p,3,-MATE,MATE,1,last,&best,0,1);data=probe(key(&p),0);candidate=data&131071;
    memset(w->history,0,sizeof w->history);memset(w->continuation,0,sizeof w->continuation);memset(w->correction,0,sizeof w->correction);
    w->correction[p.h&1023]=64;Worker *saved=malloc(sizeof *saved);assert(saved);*saved=*w;
    Entry *original_table=table;table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);clear();
    int result=search(w,&p,2,prime-1001,prime-1000,1,last,0,0,1);
    assert(result>=prime-1000&&!atomic_load(&stopped));
    assert(memcmp(w->history,saved->history,sizeof w->history)&&memcmp(w->continuation,saved->continuation,sizeof w->continuation));
    clear();*w=*saved;(void)search(w,&p,2,-MATE,MATE,1,last,0,0,1);
    assert(!atomic_load(&stopped)&&w->correction[p.h&1023]!=64&&memcmp(w->correction,saved->correction,sizeof w->correction));
    printf("ordinary learning positive controls: history/continuation changed; correction 64 -> %d: pass\n",w->correction[p.h&1023]);
    free(table);table=original_table;*w=*saved;uint64_t original_key=key(&p);Board old=p;
    result=search(w,&p,2,prime-1001,prime-1000,1,last,0,candidate,0);
    assert(result>=prime-1000&&!atomic_load(&stopped));same_learning(w,saved);
    assert(w->length==saved->length&&!memcmp(&p,&old,sizeof p)&&probe(original_key,0)==data);
    (void)search(w,&p,2,-MATE,MATE,1,last,0,candidate,0);
    assert(!atomic_load(&stopped));same_learning(w,saved);assert(probe(original_key,0)==data&&w->length==saved->length);
    *w=*saved;w->nodes=0;deadline=now()-1;uint64_t original_deadline=deadline;
    (void)search(w,&p,2,-MATE,MATE,1,last,0,candidate,0);
    assert(atomic_load(&stopped)&&deadline==original_deadline&&probe(original_key,0)==data);same_learning(w,saved);
    free(saved);puts("excluded low/wide/expired probes preserve TT, learning, board/path and original deadline: pass");
}
static void test_extension(void){
    Board p;load(&p,"6k1/1q6/8/8/8/8/1Q6/K7 w - - 0 1");Worker *w=prepare(&p);Move best=0;
    int prime=search(w,&p,3,-MATE,MATE,1,0,&best,0,1);uint64_t data=probe(key(&p),0);Move candidate=data&131071;
    assert(!atomic_load(&stopped)&&candidate==move(&p,"b2b7")&&((data>>41)&3)==1&&((data>>33)&255)>=3);
    int threshold=prime-12,alternatives=search(w,&p,2,threshold-1,threshold,1,0,0,candidate,0);
    assert(alternatives<threshold&&!atomic_load(&stopped));
    (void)search(w,&p,6,-MATE,MATE,1,0,&best,0,1);
    assert(!atomic_load(&stopped)&&w->singular_calls&&w->extensions&&best==candidate);
    Board child;assert(make(&p,candidate,&child));uint64_t child_data=probe(key(&child),0);
    printf("extension diagnostic: best=%u candidate=%u singular=%" PRIu64 " taken=%" PRIu64 " child-data=%" PRIu64 " child-depth=%" PRIu64 "\n",best,candidate,w->singular_calls,w->extensions,child_data,(child_data>>33)&255);
    printf("child key=%" PRIx64 " slot key=%" PRIx64 " slot data=%" PRIx64 " root data=%" PRIx64 "\n",key(&child),table[key(&child)&((1u<<TT_BITS)-1)].key,table[key(&child)&((1u<<TT_BITS)-1)].data,probe(key(&p),0));
    assert(child_data&&((child_data>>33)&255)>=6);
    printf("taken singular extension: prime %d alternatives %d threshold %d child TT depth %" PRIu64 " (normal 5): pass\n",prime,alternatives,threshold,(child_data>>33)&255);
}
int main(void){
    setvbuf(stdout,NULL,_IONBF,0);
    table=calloc((size_t)1<<TT_BITS,sizeof *table);assert(table);
    test_bitboards();test_see();test_singular();test_extension();free(table);return 0;
}
