/* Semantic tests of the real C search, without the protocol main.
 *
 * Compile this file together with c/board.c, selecting ROVE_VARIANT=2, 3 or 6.
 * Including search.c gives this test access to the actual excluded-search and
 * TT boundary; there is no alternate implementation used by the engine.
 */
#include "../c/search.c"
#include <assert.h>
#include <inttypes.h>

static Session session;
static Worker *workers;

static void load(Board *p,const char *fen){assert(board_fen(p,fen));assert(board_invariant(p));}
static unsigned move(const Board *p,const char *text){unsigned m=parse_move(p,text);assert(m);return m;}
static void prepare(const Board *p,uint64_t limit){
    memset(&session,0,sizeof session);session.board=*p;session.history[0]=p->key;session.history_len=1;
    session.depth=3;session.start=now_ms();session.deadline=session.start+15000;
    session.node_limit=limit;session.workers=workers;session.generation=1;
    atomic_init(&session.stop,0);atomic_init(&session.nodes,0);assert(!pthread_mutex_init(&session.mutex,NULL));
    memset(workers,0,ROVE_WORKERS*sizeof *workers);
    for(int i=0;i<ROVE_WORKERS;i++){Worker *w=&workers[i];w->id=i;w->session=&session;w->table=rove_tt;
        w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;w->path[0]=p->key;w->path_len=1;w->hint_ply=-1;}
}
static void release(void){assert(!pthread_mutex_destroy(&session.mutex));}

static void test_pals_repair(void){
    /* These callbacks are common search mechanics, not a claim that F's
     * production profile enables a split/PALS MTD scheduler. */
    Board root;board_start(&root);
    for(int black=0;black<2;black++){
        if(black){Board next;assert(make_move(&root,move(&root,"e2e4"),&next));root=next;}
        tt_clear();prepare(&root,0);
        ParallelContext context={&session,workers,session.generation*MAXPLY+2,1};
        unsigned first=move(&root,black?"a7a6":"e2e4");Board child,next;
        assert(make_move(&root,first,&child));unsigned reply=move(&child,black?"c2c4":"a7a6");
        assert(make_move(&child,reply,&next));
        RoveTask task={first,reply,2,-INF,INF,ROVE_COUNTERREPLY,0,context.generation,1};
        RoveResult r=parallel_task(&context,&task,0);
        assert(r.complete&&r.first==first&&r.reply==reply&&r.generation==task.generation&&r.depth==2);
        /* These two quiet frontiers have no capture continuation. Two plies
         * restore the root side, so the direct leaf value has root perspective. */
        assert(r.bound==ROVE_EXACT&&r.score==evaluate_reference(&next)&&r.score!=0);
        task.kind=ROVE_SELECT_REPLY;r=parallel_task(&context,&task,0);
        assert(r.complete&&r.reply&&r.reply!=reply&&make_move(&child,r.reply,&next));
        task.kind=ROVE_COUNTERREPLY;task.generation++;r=parallel_task(&context,&task,0);assert(!r.complete);
        assert(!memcmp(&session.board,&root,sizeof root));release();
    }
    board_start(&root);tt_clear();prepare(&root,0);Worker *w=&workers[0];
    ParallelContext context={&session,workers,session.generation*MAXPLY+3,1};
    unsigned first=move(&root,"e2e4");Board child;assert(make_move(&root,first,&child));
    unsigned challenged=move(&child,"a7a6"),other=move(&child,"e7e5");
    RoveTask normal={first,0,3,-INF,INF,ROVE_NORMAL,0,context.generation,1};
    RoveResult baseline=parallel_task(&context,&normal,0);assert(baseline.complete);
    w->path[0]=root.key;w->path[1]=child.key;w->path_len=2;
    uint64_t key=context_key(w,&child);
#if ROVE_VARIANT == 6
    /* Match F's actual child horizon: this is a depth-2 entry, not an entry
     * from a deeper MTD interval that would correctly be ineligible. */
    key^=UINT64_C(2)*UINT64_C(0xa0761d6478bd642f);
#endif
    tt_write(w,key,other,2,-700,1,1);
    RoveResult stale=parallel_task(&context,&normal,0);
    assert(stale.complete&&stale.score==700&&stale.nodes==1);
    w->hint=challenged;w->hint_ply=1;
    assert(move_score(w,&child,challenged,other,1)>move_score(w,&child,other,other,1));
    w->hint=0;w->hint_ply=-1;
    RoveTask repair={first,challenged,3,-INF,INF,ROVE_REPAIR,0,context.generation,1};
    RoveResult repaired=parallel_task(&context,&repair,0);
    assert(repaired.complete&&repaired.first==first&&repaired.nodes>1);
    assert(repaired.score==baseline.score&&repaired.score!=stale.score);
    RoveResult retained=parallel_task(&context,&normal,0);
    assert(retained.complete&&retained.score==baseline.score&&retained.nodes==1);
    assert(!w->hint&&w->hint_ply==-1&&!memcmp(&session.board,&root,sizeof root));release();
    root.half=100;prepare(&root,0);
    RoveTask draw_review={first,challenged,3,-1,0,ROVE_COUNTERREPLY,0,context.generation,1};
    RoveResult r=parallel_task(&context,&draw_review,0);
    assert(r.complete&&r.first==first&&r.reply==challenged&&r.score==0);
    assert(!rove_parallel_refutes(&draw_review,&r,0));
    draw_review.reply=1;r=parallel_task(&context,&draw_review,0);
    assert(!r.complete&&workers[0].path_len==session.history_len);release();
    printf("actual PALS callback: white/black reply context; ordinary TT claim %d in one node -> hinted Repair %d baseline %d nodes=%" PRIu64 "; normal TT write and drawn-root reply: pass\n",
           stale.score,repaired.score,baseline.score,repaired.nodes);
}

static void test_pals_draw_children(void){
    static const char *cycle[]={"g1f3","g8f6","f3g1","f6g8","g1f3","g8f6","f3g1"};
    for(int repetition=0;repetition<2;repetition++){
        Board root;board_start(&root);uint64_t history[10]={root.key};int len=1;
        if(repetition){
            for(size_t i=0;i<sizeof cycle/sizeof *cycle;i++){Board next;assert(make_move(&root,move(&root,cycle[i]),&next));root=next;history[len++]=root.key;}
        }else root.half=99;
        tt_clear();prepare(&root,0);memcpy(session.history,history,(size_t)len*sizeof(uint64_t));session.history_len=len;
        assert(!drawn(&root,history,len));
        unsigned first=move(&root,repetition?"f6g8":"g1f3");Board child,next;assert(make_move(&root,first,&child));
        history[len]=child.key;assert(drawn(&child,history,len+1));
        if(repetition)assert(child.half==8);else assert(child.half==100);
        unsigned reply=move(&child,repetition?"e2e4":"a7a6");assert(make_move(&child,reply,&next));
        history[len+1]=next.key;
        /* Playing this legal pawn reply would erase the already-terminal
         * child boundary and produce a nonzero quiet-frontier value. */
        assert(next.half==0&&!drawn(&next,history,len+2)&&evaluate_reference(&next)!=0);
        ParallelContext context={&session,workers,session.generation*MAXPLY+2,1};
        RoveTask task={first,reply,2,-INF,INF,ROVE_COUNTERREPLY,0,context.generation,1};
        RoveResult r=parallel_task(&context,&task,0);
        assert(r.complete&&r.first==first&&r.reply==reply&&r.generation==task.generation&&r.depth==2);
        assert(r.bound==ROVE_EXACT&&r.score==0&&r.nodes==0&&workers[0].path_len==len);
        task.kind=ROVE_NORMAL;r=parallel_task(&context,&task,0);
        assert(r.complete&&r.score==0);
        assert(!memcmp(&session.board,&root,sizeof root));release();
    }
    puts("actual PALS child draw before resetting pawn reply: halfmove-100 and legal-history threefold pass");
}

#if ROVE_VARIANT == 2
typedef struct {uint64_t key,data;} TTImage;
static TTImage tt_image(TTEntry *slot){
    /* The unit's helpers are idle here. Use the production record lock for
     * every byte read, just as a concurrent reader must. */
    assert(tt_lock(slot));TTImage image={slot->key,tt_unpack(slot)};
    atomic_store_explicit(&slot->lock,0,memory_order_release);return image;
}
static void assert_tt_image(TTEntry *slot,TTImage expected){
    TTImage actual=tt_image(slot);assert(actual.key==expected.key&&actual.data==expected.data);
}
static void test_see(void){
    static const struct {const char *label,*fen,*move;int score;} cases[]={
        {"free-pawn","7k/8/8/8/8/8/p7/R3K3 w - - 0 1","a1a2",100},
        {"losing-queen","3r3k/8/8/3p4/8/8/8/3Q3K w - - 0 1","d1d5",-800},
        {"pinned-defender","4k3/4p3/3p4/8/1B6/8/8/4R2K w - - 0 1","b4d6",100},
        {"legal-king-recapture","4k3/3p4/8/8/8/8/8/3Q3K w - - 0 1","d1d7",-800},
        {"protected-king-target","4k3/3p4/8/8/6B1/8/8/3Q3K w - - 0 1","d1d7",100},
        {"en-passant","7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1","e5d6",100},
        {"recaptured-promotion","1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7a8q",-100},
        {"promotion-capture","1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8q",1300},
        {"underpromotion-capture","1r5k/P7/8/8/8/8/8/4K3 w - - 0 1","a7b8n",720},
        {"optional-recapture","3r3k/8/8/3p4/3R4/8/8/3Q3K w - - 0 1","d4d5",100}
    };
    for(size_t i=0;i<sizeof cases/sizeof *cases;i++){
        Board p;load(&p,cases[i].fen);int actual=see(&p,move(&p,cases[i].move));
        if(actual!=cases[i].score)fprintf(stderr,"SEE %s got=%d expected=%d\n",cases[i].label,actual,cases[i].score);
        assert(actual==cases[i].score);
    }
    Board p;load(&p,"k7/8/8/4KPpr/8/8/8/8 w - g6 0 1");
    assert(!parse_move(&p,"f5g6"));assert(see(&p,MOVE(69,86,0))==-INF);
    load(&p,"4r2k/8/8/8/8/3p4/4B3/4K3 w - - 0 1");
    assert(!parse_move(&p,"e2d3"));assert(see(&p,MOVE(20,35,0))==-INF);
    load(&p,"7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1");prepare(&p,0);
    atomic_store(&session.stop,1);assert(see_for(&workers[0],&p,move(&p,"e5d6"))==SEE_INCOMPLETE);
    release();puts("see legal pins king EP promotions and incomplete cancellation: pass");
}

static void test_singular_exclusion(void){
    Board p,prior;load(&prior,"7k/6p1/8/8/8/8/PK6/8 b - - 0 1");
    unsigned last=move(&prior,"h8h7");assert(make_move(&prior,last,&p));
    tt_clear();prepare(&p,0);Worker *w=&workers[0];w->previous[0]=last;
    int prime=search(w,&p,3,-INF,INF,1,0,1);assert(!atomic_load(&session.stop)&&!w->aborted);
    uint64_t key=context_key(w,&p),data;assert(tt_read(w,key,&data,6,-INF,1));
    unsigned ttmove=(unsigned)(data&131071);assert(ttmove&&((data>>33)&127)>=3&&((data>>40)&3)==1);
    /* The candidate comes from an actual completed search, not a hand-seeded
     * score or a counter increment. At requested depth 6 its depth-3 exact TT
     * result qualifies, while it cannot itself cut off a depth-6 request. */
    uint64_t before=atomic_load(&rove_singular_calls);
    (void)search(w,&p,6,-INF,INF,1,0,1);
    assert(!atomic_load(&session.stop)&&!w->aborted);
    assert(atomic_load(&rove_singular_calls)>before);
    printf("real depth-3 TT qualified depth-6 singular probes=%" PRIu64 "\n",atomic_load(&rove_singular_calls)-before);
    release();

    tt_clear();prepare(&p,0);w=&workers[0];w->previous[0]=last;prime=search(w,&p,3,-INF,INF,1,0,1);
    key=context_key(w,&p);assert(tt_read(w,key,&data,3,-INF,1));ttmove=(unsigned)(data&131071);assert(ttmove);
    memset(w->history,0,sizeof w->history);memset(w->continuation,0,sizeof w->continuation);
    memset(w->correction,0,sizeof w->correction);memset(w->killers,0,sizeof w->killers);
    int correction_side=p.side<0,correction_index=(int)(p.pawnkey&1023);
    w->correction[correction_side][correction_index]=64;
    Worker *saved=malloc(sizeof *saved);assert(saved);*saved=*w;
    Worker *control=malloc(sizeof *control);assert(control);*control=*w;
    TTEntry *fresh=calloc((size_t)1<<ROVE_TT_BITS,sizeof *fresh);assert(fresh);control->table=fresh;
    int control_result=search(control,&p,2,prime-1001,prime-1000,1,0,1);
    assert(control_result>=prime-1000&&!atomic_load(&session.stop)&&!control->aborted);
    assert(memcmp(control->history,saved->history,sizeof w->history));
    assert(memcmp(control->continuation,saved->continuation,sizeof w->continuation));
    assert(memcmp(control->killers,saved->killers,sizeof w->killers));
    memset(fresh,0,((size_t)1<<ROVE_TT_BITS)*sizeof *fresh);*control=*saved;control->table=fresh;
    int wide_control=search(control,&p,2,-INF,INF,1,0,1);
    (void)wide_control;
    assert(control->correction[correction_side][correction_index]!=64);
    assert(memcmp(control->correction,saved->correction,sizeof w->correction));
    printf("ordinary learning positive controls: history/continuation/killers changed; correction 64 -> %d\n",
           control->correction[correction_side][correction_index]);
    free(fresh);free(control);
    TTEntry *slot=&rove_tt[key&w->table_mask];TTImage prior_entry=tt_image(slot);
    assert(prior_entry.key==key&&prior_entry.data==data);
    uint64_t saved_board_key=p.key;int saved_path=w->path_len;
    /* A low window makes a quiet alternative cut off. Learning suppression is
     * therefore exercised, rather than passing because no update qualified. */
    int result=search(w,&p,2,prime-1001,prime-1000,1,ttmove,0);
    assert(result>=prime-1000&&!atomic_load(&session.stop)&&!w->aborted);
    assert(!memcmp(w->history,saved->history,sizeof w->history));
    assert(!memcmp(w->continuation,saved->continuation,sizeof w->continuation));
    assert(!memcmp(w->correction,saved->correction,sizeof w->correction));
    assert(!memcmp(w->killers,saved->killers,sizeof w->killers));
    assert(w->path_len==saved_path&&p.key==saved_board_key&&board_invariant(&p));
    /* Descendant TT entries are valid normal searches; this specifically checks
     * that the excluded node did not publish its constrained score at this key. */
    assert_tt_image(slot,prior_entry);
    (void)search(w,&p,2,-INF,INF,1,ttmove,0);
    assert(!atomic_load(&session.stop)&&!w->aborted);
    assert(!memcmp(w->history,saved->history,sizeof w->history));
    assert(!memcmp(w->continuation,saved->continuation,sizeof w->continuation));
    assert(!memcmp(w->correction,saved->correction,sizeof w->correction));
    assert(!memcmp(w->killers,saved->killers,sizeof w->killers));
    assert_tt_image(slot,prior_entry);
    free(saved);release();puts("qualified real-TT singular search and excluded-state isolation: pass");
}

static void test_taken_singular_extension(void){
    Board p;load(&p,"6k1/1q6/8/8/8/8/1Q6/K7 w - - 0 1");tt_clear();prepare(&p,0);Worker *w=&workers[0];
    int prime=search(w,&p,3,-INF,INF,1,0,1);assert(!w->aborted&&!atomic_load(&session.stop));
    uint64_t data,key=context_key(w,&p);assert(tt_read(w,key,&data,6,-INF,1));
    unsigned candidate=(unsigned)(data&131071);assert(candidate==move(&p,"b2b7"));
    assert(((data>>33)&127)>=3&&((data>>40)&3)==1&&abs(prime)<MATE-MAXPLY);
    int threshold=prime-12,alternatives=search(w,&p,2,threshold-1,threshold,1,candidate,0);
    assert(alternatives<threshold&&!w->aborted&&!atomic_load(&session.stop));
    uint64_t before=atomic_load(&rove_singular_calls);(void)search(w,&p,6,-INF,INF,1,0,1);
    assert(atomic_load(&rove_singular_calls)>before&&!w->aborted&&!atomic_load(&session.stop));
    assert(w->pvlen[1]>0&&w->pv[1][0]==candidate);
    Board child;assert(make_move(&p,candidate,&child));w->path[w->path_len++]=child.key;
    uint64_t child_data;assert(tt_read(w,context_key(w,&child),&child_data,6,-INF,2));w->path_len--;
    int child_depth=(int)((child_data>>33)&127);
    /* A normal depth-6 parent requests depth 5 at its child. The completed
     * child entry at depth 6 is evidence that the actual extension was taken. */
    assert(child_depth>=6);
    printf("taken singular extension: real TT score %d alternatives %d threshold %d child depth %d (normal 5): pass\n",
           prime,alternatives,threshold,child_depth);release();
}
#endif

#if ROVE_VARIANT == 3
static void test_simd(void){
    Board p;board_start(&p);uint64_t state=UINT64_C(0x20261020);int checked=0;
    for(int i=0;i<400;i++){
        assert(board_invariant(&p));int reference=evaluate_reference(&p),actual=evaluate(&p);assert(reference==actual);checked++;
        Move generated[MAXMOVES];unsigned legal[MAXMOVES];int n=generate(&p,generated,0),count=0;
        for(int j=0;j<n;j++){Board next;if(make_move(&p,generated[j].m,&next))legal[count++]=generated[j].m;}
        if(!count){board_start(&p);continue;}state=state*UINT64_C(6364136223846793005)+1;
        Board next;assert(make_move(&p,legal[state%(unsigned)count],&next));p=next;
        if(i%80==79)board_start(&p);
    }
    assert(atomic_load(&rove_simd_calls)>=(uint64_t)checked);
    printf("actual AVX2 evaluation equals recomputed scalar reference: %d positions pass\n",checked);
}
#endif

#if ROVE_VARIANT == 6
/* Independent full minimax, without TT, PVS, move ordering, pruning or history
 * learning. These separated king/pawn positions have a quiet frontier; assert
 * that precondition rather than silently substituting a different qsearch. */
static int minimax(const Board *p,int depth,int ply){
    Move generated[MAXMOVES];int n=generate(p,generated,0),legal=0,best=-INF;
    for(int i=0;i<n;i++){
        Board next;if(!make_move(p,generated[i].m,&next))continue;legal++;
        if(!depth){unsigned m=generated[i].m;assert(!in_check(p));assert(!p->b[TO(m)]&&!PROM(m));
            assert(!(abs(p->b[FROM(m)])==1&&TO(m)==p->ep));}
        else{int score=-minimax(&next,depth-1,ply+1);if(score>best)best=score;}
    }
    if(!legal)return in_check(p)?-MATE+ply:0;
    return depth?best:evaluate_reference(p);
}
static int chosen_score(const Board *p,unsigned m,int depth){
    char text[8];assert(m);move_string(m,text);assert(parse_move(p,text)==m);
    Board next;assert(make_move(p,m,&next));return -minimax(&next,depth-1,1);
}
static void test_mtd(void){
    static const char *positions[]={
        "8/6pk/8/8/8/8/PK6/8 w - - 0 1",
        "8/6pk/8/8/8/P7/1K6/8 b - - 0 1",
        "8/7k/6p1/8/8/P7/1K6/8 w - - 0 1"
    };
    for(size_t i=0;i<sizeof positions/sizeof *positions;i++){
        Board p;load(&p,positions[i]);int expected=minimax(&p,3,0);tt_clear();prepare(&p,0);
        uint64_t converged=atomic_load(&rove_mtd_converged),conflicts=atomic_load(&rove_mtd_conflicts),probes=atomic_load(&rove_mtd_probes);
        run_parallel(&session,workers);
        assert(session.completed_depth==3&&!atomic_load(&session.stop));
        assert(session.score==expected&&session.best&&chosen_score(&p,session.best,3)==expected);
        assert(atomic_load(&rove_mtd_converged)-converged==3&&atomic_load(&rove_mtd_probes)>probes);
        assert(atomic_load(&rove_mtd_conflicts)==conflicts);release();
        /* Keep the actual TT. A new go restarts from shallow depth; old deeper
         * bounds must not be merged into that different-horizon interval. */
        prepare(&p,0);run_parallel(&session,workers);
        assert(session.completed_depth==3&&!atomic_load(&session.stop)&&session.score==expected);
        assert(session.best&&chosen_score(&p,session.best,3)==expected);release();
        for(int shallow=1;shallow<=2;shallow++){
            prepare(&p,0);session.depth=shallow;run_parallel(&session,workers);
            assert(session.completed_depth==shallow&&!atomic_load(&session.stop));
            assert(session.score==minimax(&p,shallow,0));
            assert(session.best&&chosen_score(&p,session.best,shallow)==session.score);release();
        }
        printf("MTD exact minimax, legal attaining witness, repeated horizon case %zu: pass\n",i);
    }
    Board p;load(&p,positions[0]);tt_clear();prepare(&p,100);session.depth=8;
    run_parallel(&session,workers);assert(atomic_load(&session.stop)&&atomic_load(&session.nodes)<=100);
    assert(session.completed_depth>0&&session.completed_depth<8);
    assert(session.score==minimax(&p,session.completed_depth,0));
    assert(session.best&&chosen_score(&p,session.best,session.completed_depth)==session.score);
    printf("MTD cancellation preserved completed depth %d score %d with nodes=%" PRIu64 ": pass\n",
           session.completed_depth,session.score,atomic_load(&session.nodes));release();
}
#endif

int main(void){
    board_init();evaluate_init();rove_tt=calloc((size_t)1<<ROVE_TT_BITS,sizeof *rove_tt);assert(rove_tt);
    workers=calloc(ROVE_WORKERS,sizeof *workers);assert(workers);assert(parallel_init());tt_clear();
    test_pals_repair();test_pals_draw_children();
#if ROVE_VARIANT == 2
    test_see();test_singular_exclusion();test_taken_singular_extension();
#elif ROVE_VARIANT == 3
    test_simd();
#elif ROVE_VARIANT == 6
    test_mtd();
#else
#error search_contract.c supports ROVE_VARIANT 2, 3 and 6
#endif
    parallel_shutdown();free(workers);free(rove_tt);puts("search semantic contract: pass");return 0;
}
