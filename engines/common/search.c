/* Shared search support: budget claims, piece indexing, TT publication and
 * history learning. Family-owned search algorithms and table layouts remain
 * in the templates; different data-publication expressions stay separate. */

/* rove:begin claim */
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
/* rove:end claim */

/* rove:begin piece_index */
static int piece_index(int p){return p+6;}
/* rove:end piece_index */

/* rove:begin probe */
static uint64_t probe(uint64_t key,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;
    if(data)e->key=key,e->data=data;
    else data=e->key==key?e->data:0;
    atomic_flag_clear_explicit(&e->lock,memory_order_release);
    return data;
}
/* rove:end probe */

/* rove:begin probe_explicit_write */
static uint64_t probe(uint64_t key,int write,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;
    if(write)e->key=key,e->data=data;
    else data=e->key==key?e->data:0;
    atomic_flag_clear_explicit(&e->lock,memory_order_release);
    return data;
}
/* rove:end probe_explicit_write */

/* rove:begin learn_signed */
static void learn(int16_t *cell,int bonus){
    *cell+=(bonus-*cell*abs(bonus)/16384);
}
/* rove:end learn_signed */
