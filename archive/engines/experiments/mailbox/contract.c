/* Compiled against each complete generated A core, independently of its UCI.
 * Differential copy code retains the original canonical make implementation.
 */
#include "rove.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

static uint64_t nodes, moves, specials, checksum;
static void require(int ok,const char *what){if(!ok){fprintf(stderr,"contract failure: %s at node %" PRIu64 "\n",what,nodes);exit(1);}}
static void visit(Board *p,int depth){
    nodes++;require(board_invariant(p),"board/hash/HCE/bitboard invariant");
    require(evaluate(p)==evaluate_reference(p),"incremental/reference HCE");
    checksum^=p->key+(uint64_t)(unsigned)p->hce*UINT64_C(0x9e3779b97f4a7c15);
    if(!depth)return;
    Move list[MAXMOVES];int n=generate(p,list,0);
    for(int i=0;i<n;i++){
        Board before=*p,reference;unsigned m=list[i].m;
        int legal=copy_reference(p,m,&reference);
#if MB_UNMAKE
        Undo undo;int actual=make_inplace(p,m,&undo);
        require(actual==legal,"copy/inplace legality");
        if(actual){
            require(!memcmp(p,&reference,sizeof *p),"copy/inplace exact child");
            moves++;if(PROM(m)||abs(before.b[FROM(m)])==6&&abs((int)TO(m)-(int)FROM(m))==2||TO(m)==before.ep)specials++;
            visit(p,depth-1);unmake(p,&undo);
        }
        require(!memcmp(p,&before,sizeof *p),"exact board restoration including illegal move");
#else
        if(legal){moves++;if(PROM(m)||abs(before.b[FROM(m)])==6&&abs((int)TO(m)-(int)FROM(m))==2||TO(m)==before.ep)specials++;visit(&reference,depth-1);}
        require(!memcmp(p,&before,sizeof *p),"copy parent immutable");
#endif
    }
}
int main(void){
    const struct {const char *fen;int depth;} fixtures[]={
        {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",3},
        {"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",3},
        {"8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",3},
        {"r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 19 42",3},
        {"4k3/P6p/8/3pP3/8/8/7P/4K3 w - d6 0 10",4},
        {"k3r3/8/8/3pP3/8/8/8/4K3 w - d6 99 37",3},
        {"4k3/8/8/8/8/8/p6P/4K3 b - - 99 37",3}
    };
    board_init();evaluate_init();
    for(size_t i=0;i<sizeof fixtures/sizeof fixtures[0];i++){Board p;require(board_fen(&p,fixtures[i].fen),"fixture FEN");Board before=p;visit(&p,fixtures[i].depth);require(!memcmp(&p,&before,sizeof p),"whole traversal restoration");}
    rove_tt=calloc((size_t)1<<ROVE_TT_BITS,sizeof *rove_tt);require(rove_tt!=NULL,"TT allocation");
    Session *s=calloc(1,sizeof *s);Worker *w=calloc(1,sizeof *w);require(s&&w,"worker allocation");
    w->session=s;w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;
    const int limits[]={1,2,3,7,31,64,127,256,511,2048};
    for(size_t j=0;j<sizeof limits/sizeof limits[0];j++){
        Board p;board_start(&p);Board before=p;tt_clear();memset(w,0,sizeof *w);w->session=s;w->table=rove_tt;w->table_mask=((size_t)1<<ROVE_TT_BITS)-1;
        w->path[0]=p.key;w->path_len=1;s->node_limit=limits[j];atomic_store(&s->nodes,0);atomic_store(&s->stop,0);
        (void)search(w,&p,8,-INF,INF,0,0,1);
        require(atomic_load(&s->stop),"actual recursive cancellation reached");
        require(w->path_len==1&&w->path[0]==before.key,"history length/root restored after cancellation");
        require(!memcmp(&p,&before,sizeof p),"search board restored after cancellation");
        require(board_invariant(&p),"search canceled invariant");
    }
    printf("{\"board_bytes\":%zu,\"worker_bytes\":%zu,\"undo_bytes\":%zu,\"nodes\":%" PRIu64 ",\"moves\":%" PRIu64 ",\"special_moves\":%" PRIu64 ",\"checksum\":\"%016" PRIx64 "\",\"cancel_budgets\":%zu}\n",sizeof(Board),sizeof(Worker),
#if MB_UNMAKE
        sizeof(Undo),
#else
        (size_t)0,
#endif
        nodes,moves,specials,checksum,sizeof limits/sizeof limits[0]);
    free(s);free(w);free(rove_tt);return 0;
}
