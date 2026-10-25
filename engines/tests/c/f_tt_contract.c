/* Actual F TT contract, compiled with c/board.c and ROVE_VARIANT=6.
 *
 * This includes the canonical implementation rather than a model of its TT.
 * Run both ROVE_F_SINGLE=0 and =1, optionally with ROVE_F_PARITY=0/1. Output
 * belongs outside the repository. This is a correctness experiment; elapsed
 * time and successful-read counts do not establish performance or scaling.
 */
#include "../../c/search.c"
#include <assert.h>
#include <inttypes.h>
#include <sched.h>

#if ROVE_VARIANT != 6
#error tt_contract.c requires ROVE_VARIANT=6
#endif

#define STRESS_THREADS 8
#define STRESS_ROUNDS 60000

static const uint64_t key_a=UINT64_C(0xfedcba9876543201);
static const unsigned witness=MOVE(16,48,0);

static uint64_t packed(unsigned m,int depth,int score,int bound,int ply){
    /* Independent representation expectation, including root-relative mates. */
    int normalized=score;
    if(score>MATE-MAXPLY)normalized+=ply;
    if(score<-MATE+MAXPLY)normalized-=ply;
    return (uint64_t)m|((uint64_t)(uint16_t)(int16_t)normalized<<17)
        |((uint64_t)depth<<33)|((uint64_t)bound<<40);
}

static Worker *new_worker(void){
    Worker *w=calloc(1,sizeof *w);assert(w);
    w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;
    return w;
}

static uint64_t read_required(Worker *w,uint64_t key,int depth,int alpha,int ply){
    uint64_t data=0;assert(tt_read(w,key,&data,depth,alpha,ply));return data;
}

static void test_fields_and_keys(Worker *w){
    static const int depths[]={0,1,31,63,95,127};
    static const int scores[]={-20000,-1,0,1,20000,-MATE+9,MATE-9};
    unsigned samples=0;
    for(size_t di=0;di<sizeof depths/sizeof *depths;di++)
    for(size_t si=0;si<sizeof scores/sizeof *scores;si++)
    for(int bound=1;bound<=3;bound++){
        tt_clear();int depth=depths[di],score=scores[si],write_ply=7;
        unsigned m=si&1?MOVE(113,119,5):witness;
        tt_write(w,key_a,m,depth,score,bound,write_ply);
        uint64_t d=read_required(w,key_a,depth,INF,write_ply);
        assert(d==packed(m,depth,score,bound,write_ply));
        assert(score_from_tt((int16_t)(d>>17),write_ply)==score);
        int at_two=score;
        if(score>MATE-MAXPLY)at_two+=write_ply-2;
        if(score<-MATE+MAXPLY)at_two-=write_ply-2;
        assert(score_from_tt((int16_t)(d>>17),2)==at_two);
        uint64_t ignored;
        assert(!tt_read(w,key_a^UINT64_C(0x8000000000000000),&ignored,depth,INF,2));
        assert(!tt_read(w,key_a^UINT64_C(0x0001000000000000),&ignored,depth,INF,2));
        samples++;
    }
    /* A zero evaluation and null move are still a present exact record. */
    tt_clear();tt_write(w,key_a,0,0,0,1,0);
    assert(read_required(w,key_a,0,0,0)==packed(0,0,0,1,0));
    const uint64_t replacement=key_a^UINT64_C(0x1800000000000000);
    tt_write(w,replacement,witness,4,18,1,0);uint64_t ignored;
    assert(!tt_read(w,key_a,&ignored,4,INF,0));
    assert(read_required(w,replacement,4,INF,0)==packed(witness,4,18,1,0));
    tt_clear();assert(!tt_read(w,replacement,&ignored,4,INF,0));
    printf("full64 keys, collision replacement, all bounds/depths/mate plies: %u cases pass\n",samples);
}

static void test_direction_retention(Worker *w){
    tt_clear();unsigned lower_move=MOVE(16,48,0),upper_move=MOVE(17,49,0);
    uint64_t lower=packed(lower_move,6,40,2,0),upper=packed(upper_move,6,50,3,0);
    tt_write(w,key_a,lower_move,6,40,2,0);
    tt_write(w,key_a,upper_move,6,50,3,0);
#if ROVE_F_SINGLE
    assert(read_required(w,key_a,6,-INF,0)==upper);
    assert(read_required(w,key_a,6,INF,0)==upper);
#else
    assert(read_required(w,key_a,6,-INF,0)==lower);
    assert(read_required(w,key_a,6,INF,0)==upper);
    /* The upper direction is only preferred when its horizon also matches. */
    assert(read_required(w,key_a,5,INF,0)==lower);
#endif
    tt_write(w,key_a,lower_move,6,45,2,0);
    assert(read_required(w,key_a,6,-INF,0)==packed(lower_move,6,45,2,0));
#if !ROVE_F_SINGLE
    assert(read_required(w,key_a,6,INF,0)==upper);
#endif
    tt_write(w,key_a,witness,6,47,1,0);
    assert(read_required(w,key_a,6,-INF,0)==packed(witness,6,47,1,0));
    assert(read_required(w,key_a,6,INF,0)==packed(witness,6,47,1,0));
    printf("opposite bounds: %s; later exact replaces both visible directions: pass\n",
        ROVE_F_SINGLE?"single last-write replacement":"paired direction preservation");
}

static void test_busy_slot(Worker *w){
    tt_clear();tt_write(w,key_a,witness,3,71,2,0);
    TTEntry *e=&w->table[key_a&w->table_mask];assert(tt_lock(e));
#if ROVE_F_SINGLE
    uint64_t saved_key=e->key,saved_data=tt_unpack(e),ignored;
#else
    uint64_t saved_key=e->key,saved_data=e->data,saved_upper=e->upper_data,ignored;
#endif
    assert(!tt_read(w,key_a,&ignored,3,0,0));
    tt_write(w,key_a,MOVE(17,49,0),4,-999,3,0);
#if ROVE_F_SINGLE
    assert(e->key==saved_key&&tt_unpack(e)==saved_data);
    tt_clear();assert(e->key==saved_key&&tt_unpack(e)==saved_data);
#else
    assert(e->key==saved_key&&e->data==saved_data&&e->upper_data==saved_upper);
    tt_clear();assert(e->key==saved_key&&e->data==saved_data&&e->upper_data==saved_upper);
#endif
    /* During a write there may temporarily be a mixed key/data pair. Build
     * exactly the XOR alias that the previous optimistic publication accepted.
     * The byte lock must turn both its real-key and artificial-key probes into
     * misses, without inspecting any non-atomic fields in tt_read. */
    uint64_t changed=packed(witness,3,72,2,0),alias=saved_key^saved_data^changed;
    assert(alias!=saved_key&&(alias&w->table_mask)==(saved_key&w->table_mask));
#if ROVE_F_SINGLE
    for(int i=0;i<7;i++)e->data[i]=(unsigned char)(changed>>(i*8));
#else
    e->data=changed;
#endif
    assert(!tt_read(w,saved_key,&ignored,3,0,0));
    assert(!tt_read(w,alias,&ignored,3,0,0));
#if ROVE_F_SINGLE
    for(int i=0;i<7;i++)e->data[i]=(unsigned char)(saved_data>>(i*8));
#else
    e->data=saved_data;
#endif
    atomic_store_explicit(&e->lock,0,memory_order_release);
    assert(read_required(w,key_a,3,0,0)==saved_data);
    tt_write(w,key_a,witness,3,72,2,0);
    assert(read_required(w,key_a,3,0,0)==packed(witness,3,72,2,0));
    tt_clear();assert(!tt_read(w,key_a,&ignored,3,0,0));
    puts("held slot: reads and synthetic publication alias miss, writes/clear skip, record recovers: pass");
}

static void prepare_search(Worker *w,Session *s,const Board *p){
    memset(s,0,sizeof *s);memset(w,0,sizeof *w);
    s->board=*p;s->history[0]=p->key;s->history_len=1;
    s->start=now_ms();s->deadline=s->start+10000;
    atomic_init(&s->stop,0);atomic_init(&s->nodes,0);
    w->session=s;w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;
    w->path[0]=p->key;w->path_len=1;w->hint_ply=-1;
}

static void test_real_search_horizon(Worker *w){
    Board p;assert(board_fen(&p,"8/6pk/8/8/8/8/PK6/8 w - - 0 1"));
    assert(board_invariant(&p));Session *s=calloc(1,sizeof *s);assert(s);
    tt_clear();prepare_search(w,s,&p);
    int expected=search(w,&p,2,-INF,INF,1,0,1);
    assert(!w->aborted&&!atomic_load(&s->stop));
    /* Positive control: an exact, matching-horizon non-root record cuts off. */
    tt_clear();prepare_search(w,s,&p);
    uint64_t key=context_key(w,&p)^(UINT64_C(2)*UINT64_C(0xa0761d6478bd642f));
    tt_write(w,key,witness,2,12345,1,1);
    assert(search(w,&p,2,-INF,INF,1,0,1)==12345&&w->nodes==1);
    /* Same bucket/key but wrong metadata must not return the artificial score. */
    tt_clear();prepare_search(w,s,&p);tt_write(w,key,witness,3,12345,1,1);
    assert(search(w,&p,2,-INF,INF,1,0,1)==expected&&w->nodes>1);
    assert(!w->aborted&&!atomic_load(&s->stop));
    /* Retain completed real entries, then search another depth and return. */
    prepare_search(w,s,&p);(void)search(w,&p,3,-INF,INF,1,0,1);
    assert(!w->aborted&&!atomic_load(&s->stop));
    prepare_search(w,s,&p);assert(search(w,&p,2,-INF,INF,1,0,1)==expected);
    assert(!w->aborted&&!atomic_load(&s->stop));free(s);
    puts("actual search: matching-horizon cutoff positive control, depth mismatch and retained TT: pass");
}

typedef struct {
    Worker *w;unsigned id;uint64_t writes,reads,hits;
    _Atomic unsigned *ready,*start;
} Stress;

static uint64_t stress_key(unsigned id){
    return UINT64_C(0xa000000000001f01)^((uint64_t)(id+1)<<48);
}

static uint64_t stress_data(unsigned id,int bound){
    return packed(MOVE(16+(int)id,48+(int)id,0),5+(int)id,100+(int)id*37,bound,0);
}

static void *stress_thread(void *arg){
    Stress *s=arg;unsigned id=s->id;uint64_t key=stress_key(id);
    atomic_fetch_add_explicit(s->ready,1,memory_order_release);
    while(!atomic_load_explicit(s->start,memory_order_acquire))sched_yield();
    for(unsigned i=0;i<STRESS_ROUNDS;i++){
        int bound=(i&1)?3:2;
        tt_write(s->w,key,MOVE(16+(int)id,48+(int)id,0),5+(int)id,100+(int)id*37,bound,0);
        s->writes++;
        for(unsigned offset=0;offset<2;offset++){
            unsigned target=(id+offset)%STRESS_THREADS;uint64_t data=0;s->reads++;
            if(tt_read(s->w,stress_key(target),&data,5+(int)target,(i&2)?INF:-INF,0)){
                assert(data==stress_data(target,2)||data==stress_data(target,3));s->hits++;
            }
        }
    }
    return NULL;
}

static void test_contested_slot(void){
    tt_clear();pthread_t threads[STRESS_THREADS];Stress states[STRESS_THREADS];
    _Atomic unsigned ready=0,start=0;uint64_t hits=0,reads=0,writes=0;
    for(unsigned i=0;i<STRESS_THREADS;i++){
        states[i]=(Stress){new_worker(),i,0,0,0,&ready,&start};
        assert((stress_key(i)&states[i].w->table_mask)==(stress_key(0)&states[i].w->table_mask));
        assert(!pthread_create(&threads[i],NULL,stress_thread,&states[i]));
    }
    while(atomic_load_explicit(&ready,memory_order_acquire)<STRESS_THREADS)sched_yield();
    atomic_store_explicit(&start,1,memory_order_release);
    for(unsigned i=0;i<STRESS_THREADS;i++){
        assert(!pthread_join(threads[i],NULL));hits+=states[i].hits;reads+=states[i].reads;
        writes+=states[i].writes;free(states[i].w);
    }
    assert(hits>0);
    /* Every successful read was matched to its complete originating tuple.
     * A miss is valid under contention, especially for the single byte lock. */
    printf("actual same-slot contention: threads=%d write attempts=%" PRIu64
        " reads=%" PRIu64 " coherent hits=%" PRIu64 ": pass\n",
        STRESS_THREADS,writes,reads,hits);
}

int main(void){
    assert(sizeof(TTEntry)==(ROVE_F_SINGLE?16:32));board_init();evaluate_init();
    rove_tt=calloc((size_t)1<<ROVE_TT_BITS,sizeof *rove_tt);assert(rove_tt);
    Worker *w=new_worker();
    test_fields_and_keys(w);test_direction_retention(w);test_busy_slot(w);
    test_real_search_horizon(w);test_contested_slot();
    free(w);free(rove_tt);
    printf("F TT contract single=%d parity=%d bytes=%zu: pass\n",
        ROVE_F_SINGLE,ROVE_F_PARITY,sizeof(TTEntry));return 0;
}
