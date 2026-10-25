#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>

/* The approved command resolves this to the pinned cost candidate input.
 * The actual static probe body is included unchanged, with no test hooks.
 * Uncalled search/think sections are discarded by the fixture link. */
#include "search.c"

Entry *table;
static atomic_int failure, ready, gate;
static atomic_uint attempts[2], observations, hits;
static const uint64_t keys[2] = {UINT64_C(0x0123456789abcdef), UINT64_C(0x8123456789abcdef)};
static const uint64_t words[2] = {UINT64_C(0x8000000040010001), UINT64_C(0x7fffffffbffe0002)};
enum { WRITES = 50000, READS = 100000 };
_Static_assert(TT_BITS==18 && WORKERS==2 && PLY==128, "fixed candidate resources");
_Static_assert((UINT64_C(0x0123456789abcdef)&((1u<<TT_BITS)-1)) ==
               (UINT64_C(0x8123456789abcdef)&((1u<<TT_BITS)-1)), "colliding full keys");

static int check(int condition,int code){
    if(!condition){int expected=0;atomic_compare_exchange_strong(&failure,&expected,code);}
    return condition;
}

/* These are the unchanged public integer TT payload expressions in search.c;
 * literal expected words below independently bind the actual bit format. */
static uint64_t packed(Move bestmove,int score,int depth,int bound,int ply){
    if(score>MATE-PLY)score+=ply;
    if(score< -MATE+PLY)score-=ply;
    return bestmove|((uint64_t)(uint16_t)score<<17)|
        ((uint64_t)(depth>0?depth:0)<<33)|((uint64_t)bound<<41);
}

static int unpacked_score(uint64_t data,int ply){
    int score=(int16_t)(data>>17);
    if(score>MATE-PLY)score-=ply;
    if(score< -MATE+PLY)score+=ply;
    return score;
}

static void serial(void){
    check(probe(keys[0],0,0)==0 && probe(keys[1],0,0)==0,10);
    probe(keys[0],1,words[0]);
    check(probe(keys[0],0,0)==words[0] && probe(keys[1],0,0)==0,11);
    probe(keys[1],1,words[1]);
    check(probe(keys[1],0,0)==words[1] && probe(keys[0],0,0)==0,12);
    probe(0,1,UINT64_MAX);
    check(probe(0,0,0)==UINT64_MAX && probe(UINT64_C(1)<<63,0,0)==0,13);
    const struct {Move move;int score,ply,depth,bound;uint64_t word;} cases[] = {
        {772,123,0,0,1,UINT64_C(0x20000f60304)},
        {4112,-123,7,-3,3,UINT64_C(0x601ff0a1010)},
        {96352,29995,5,126,2,UINT64_C(0x4fcea617860)},
        {772,-29995,5,64,1,UINT64_C(0x28115a00304)}
    };
    for(unsigned i=0;i<sizeof cases/sizeof *cases;i++){
        uint64_t key=UINT64_C(0xf123000000000010)+i;
        uint64_t word=packed(cases[i].move,cases[i].score,cases[i].depth,cases[i].bound,cases[i].ply);
        check(word==cases[i].word,20+(int)i);
        probe(key,1,word);
        uint64_t got=probe(key,0,0);
        check(got==cases[i].word && (got&131071)==cases[i].move &&
              ((got>>41)&3)==(unsigned)cases[i].bound &&
              ((got>>33)&255)==(unsigned)(cases[i].depth>0?cases[i].depth:0) &&
              unpacked_score(got,cases[i].ply)==cases[i].score,30+(int)i);
        if(cases[i].score>MATE-PLY)check(unpacked_score(got,3)==29997,40);
        if(cases[i].score< -MATE+PLY)check(unpacked_score(got,3)==-29997,41);
    }
}

static void arrive(void){
    atomic_fetch_add_explicit(&ready,1,memory_order_release);
    while(!atomic_load_explicit(&gate,memory_order_acquire))sched_yield();
}

static void *writer(void *argument){
    unsigned id=*(unsigned *)argument;
    arrive();
    for(unsigned i=0;i<WRITES && !atomic_load(&failure);i++){
        /* probe's return is not a CAS-success acknowledgement. */
        probe(keys[id],1,words[id]);
        atomic_fetch_add(&attempts[id],1);
    }
    return 0;
}

static void *reader(void *unused){
    (void)unused;
    arrive();
    for(unsigned i=0;i<READS && !atomic_load(&failure);i++)for(unsigned id=0;id<2;id++){
        uint64_t got=probe(keys[id],0,0);
        /* Replacement or a dropped write may produce a miss. A hit must carry
         * the entire exact payload associated with this entire exact key. */
        check(got==0 || got==words[id],50+(int)id);
        atomic_fetch_add(&observations,1);
        if(got)atomic_fetch_add(&hits,1);
    }
    return 0;
}

int main(void){
    size_t bytes=((size_t)1<<TT_BITS)*sizeof *table;
    table=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(table==MAP_FAILED)return 2;
    check(((uintptr_t)table&15)==0,1);
    serial();
    pthread_t threads[3];unsigned ids[2]={0,1};int created=0,joined=1;
    if(!atomic_load(&failure)){
        for(int i=0;i<3;i++){
            int error=pthread_create(threads+i,0,i<2?writer:reader,i<2?ids+i:0);
            if(error){check(0,60+i);break;}
            created++;
        }
        if(created==3)while(atomic_load_explicit(&ready,memory_order_acquire)!=3)sched_yield();
        atomic_store_explicit(&gate,1,memory_order_release);
        for(int i=0;i<created;i++)if(pthread_join(threads[i],0)){check(0,70+i);joined=0;}
    }
    if(joined){
        /* Only uncontended writes are required to become visible. */
        probe(keys[0],1,words[0]);
        check(probe(keys[0],0,0)==words[0] && probe(keys[1],0,0)==0,80);
        check(munmap(table,bytes)==0,81);
    }
    int code=atomic_load(&failure);
    printf("{\"complete\":%s,\"failure_code\":%d,\"entry_bytes\":%zu,\"entry_align\":%zu,"
           "\"table_bytes\":%zu,\"writers\":2,\"reader\":1,\"created\":%d,\"joined\":%s,"
           "\"write_attempts\":[%u,%u],\"observations\":%u,\"hits\":%u,"
           "\"contended_miss_or_drop_allowed\":true,\"CAS_drop_causality_observed\":false,"
           "\"engine_entry_executed\":false}\n",
           code?"false":"true",code,sizeof(Entry),(size_t)_Alignof(Entry),bytes,created,
           joined?"true":"false",atomic_load(attempts),atomic_load(attempts+1),
           atomic_load(&observations),atomic_load(&hits));
    return code?2:0;
}
