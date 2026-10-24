/* Recipe renders table-eval.c.in as table-eval.c before compilation.
 * Use the frozen TinyCE core: -I core -DDEV=1 -mavx2. */
#ifndef TINY_C_TABLE_PRODUCTION_INCLUDED
#include "tiny.h"
#include "board.c"
#include "table-eval.c"
#endif
#include <assert.h>

static uint64_t random_state=UINT64_C(0x4b49514d9c7af523);
static unsigned random_number(void){
    random_state^=random_state<<13;
    random_state^=random_state>>7;
    random_state^=random_state<<17;
    return (unsigned)random_state;
}
static unsigned positions;
static void parity(Board *p){
    Board before=*p;
    int scalar=tiny_scalar(p),simd=tiny_raw(p);
    assert(scalar==simd);
    assert(!memcmp(&before,p,sizeof before));
    p->s=-p->s;p->v=INT_MIN;
    assert(tiny_raw(p)==scalar);
    *p=before;
    assert(tiny_order(p,MOVE(0,16,0))==0);
    ++positions;
}
int main(int argc,char **argv){
    /* The constructor must finish exactly once before main and, in the real
     * engine, before any worker sees a table. Never initialize it manually. */
    assert(atomic_load(&tiny_init_calls)==1);
    for(int v=-6;v<=6;v++)for(int sq=0;sq<64;sq++)
        assert(tiny_table[(v+6)*64+sq]==value(v,(sq/8)*16+sq%8));
    assert(sizeof tiny_table==832*4);
    if(argc==2&&!strcmp(argv[1],"--dump-table")){
        /* Explicit little-endian signed-32 bytes for representation hashes. */
        for(int i=0;i<832;i++){
            uint32_t v=(uint32_t)tiny_table[i];
            for(int b=0;b<4;b++)assert(putchar((int)((v>>(8*b))&255))!=EOF);
        }
        return 0;
    }
    assert(argc==1);
    Board p;
    for(int square=0;square<128;square++)if(!(square&0x88)){
        for(int piece=-6;piece<=6;piece++){
            memset(&p,0,sizeof p);p.s=1;p.b[square]=(int8_t)piece;
            for(int q=8;q<128;q+=16)memset(p.b+q,0x7f,8);
            parity(&p);
        }
    }
    const char *specials[]={
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/P6p/8/8/8/8/p6P/4K3 w - - 0 1",
        "6k1/8/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"
    };
    for(unsigned s=0;s<sizeof specials/sizeof *specials;s++){
        assert(fen(&p,specials[s]));parity(&p);
        Move moves[MOVES];int n=gen(&p,moves);
        for(int i=0;i<n;i++){Board child;if(make(&p,moves[i],&child))parity(&child);}
    }
    start(&p);
    for(int step=0;step<12000;step++){
        assert(verify_board(&p));parity(&p);
        Move moves[MOVES],legal[MOVES];int n=gen(&p,moves),count=0;
        for(int i=0;i<n;i++){
            Board child;
            if(make(&p,moves[i],&child)){parity(&child);legal[count++]=moves[i];}
        }
        if(!count||p.half>=90||step%127==126){start(&p);continue;}
        Board child;assert(make(&p,legal[random_number()%count],&child));p=child;
    }
    assert(atomic_load(&tiny_leaf_calls)==(uint64_t)positions*2);
    assert(!atomic_load(&tiny_order_calls));
    assert(atomic_load(&tiny_init_calls)==1);
    printf("{\"table_terms\":832,\"table_bytes\":3328,\"init_calls\":1,\"positions\":%u,\"avx2_leaf_calls\":%llu,\"parity\":true,\"board_preserved\":true}\n",
        positions,(unsigned long long)atomic_load(&tiny_leaf_calls));
    return 0;
}
