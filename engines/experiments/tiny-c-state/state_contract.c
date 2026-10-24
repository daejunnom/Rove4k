/* Focused actual-DEV=0 differential fixture. The two adapters contain separate
 * frozen production translation units; FEN is an explicitly fixture-only copy
 * of the original DEV ingress. No shipping parser or algorithm is replaced. */
#include "state_contract.h"
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { MAX_MOVES=512, RANDOM_PLIES=5000 };
typedef struct { void *baseline,*candidate; } Pair;
static uint64_t random_state=UINT64_C(0x37be54c1fa638209);
static uint64_t digest[2]={UINT64_C(14695981039346656037),UINT64_C(14695981039346656037)};
static uint64_t positions,legal_children,pseudo_moves;

static unsigned random_number(void){
    random_state^=random_state<<13;
    random_state^=random_state>>7;
    random_state^=random_state<<17;
    return (unsigned)random_state;
}
static uint64_t reference_mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
static int reference_value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7),score=material[a];
    if(a==1)score+=advance*7+center*2;
    if(a==2)score+=center*9;
    if(a==3)score+=center*5;
    if(a==4)score+=advance*2;
    if(a==5)score+=center*2;
    if(a==6)score-=center*3;
    return v>0?score:-score;
}
static void hash_word(int index,uint64_t value,int bytes){
    for(int i=0;i<bytes;i++){
        digest[index]^=(value>>(8*i))&255;
        digest[index]*=UINT64_C(1099511628211);
    }
}
static void hash_snapshot(int index,const RoveStateSnapshot *s,int raw,uint64_t key,int dead){
    for(int q=0;q<128;q++)hash_word(index,(uint8_t)s->cells[q],1);
    hash_word(index,(uint32_t)s->side,4);
    hash_word(index,(uint32_t)s->rights,4);
    hash_word(index,(uint32_t)s->ep,4);
    hash_word(index,(uint32_t)s->kings[0],4);
    hash_word(index,(uint32_t)s->kings[1],4);
    hash_word(index,(uint32_t)s->halfmove,4);
    hash_word(index,s->hash,8);hash_word(index,s->reversible,8);
    hash_word(index,(uint32_t)raw,4);hash_word(index,key,8);
    hash_word(index,(uint32_t)dead,4);
}
static int reference_scalar(const RoveStateSnapshot *s){
    int scalar=0,counts[2]={0},kings[2]={0};
    assert(s->side==1||s->side==-1);
    assert(s->rights>=0&&s->rights<=15&&s->halfmove>=0);
    assert(s->ep==-1||(!(s->ep&0x88)&&s->ep>=0&&s->ep<128));
    for(int q=0;q<128;q++){
        int v=s->cells[q];assert(abs(v)<=6);
        if(q&0x88){assert(!v);continue;}
        scalar+=reference_value(v,q);
        if(v){
            assert(++counts[v<0]<=16);
            if(abs(v)==6){assert(s->kings[v<0]==q);kings[v<0]++;}
        }
    }
    assert(kings[0]==1&&kings[1]==1);
    assert(abs(scalar)<=29120);
    return scalar;
}
static void equal_snapshot(const RoveStateSnapshot *a,const RoveStateSnapshot *b){
    assert(!memcmp(a->cells,b->cells,sizeof a->cells));
    assert(a->side==b->side&&a->rights==b->rights&&a->ep==b->ep);
    assert(a->kings[0]==b->kings[0]&&a->kings[1]==b->kings[1]);
    assert(a->halfmove==b->halfmove&&a->hash==b->hash&&a->reversible==b->reversible);
}
static RoveStateSnapshot compare_position(const Pair *p){
    RoveStateSnapshot a,b;
    rove_state_baseline.snapshot(p->baseline,&a);
    rove_state_candidate.snapshot(p->candidate,&b);
    equal_snapshot(&a,&b);
    int scalar=reference_scalar(&a);
    int avx_a=rove_state_baseline.raw(p->baseline),avx_b=rove_state_candidate.raw(p->candidate);
    assert(avx_a==scalar&&avx_b==scalar);
    assert(rove_state_baseline.cached_white(p->baseline)==scalar);
    int dead_a=rove_state_baseline.dead_position(p->baseline);
    int dead_b=rove_state_candidate.dead_position(p->candidate);
    assert(dead_a==dead_b);
    uint64_t key_a=rove_state_baseline.tt_key(p->baseline),key_b=rove_state_candidate.tt_key(p->candidate);
    assert(key_a==key_b&&key_a==(a.hash^reference_mix(a.reversible+(unsigned)a.halfmove)));
    hash_snapshot(0,&a,avx_a,key_a,dead_a);hash_snapshot(1,&b,avx_b,key_b,dead_b);
    positions++;return a;
}
static Pair allocate_pair(void){
    Pair p={malloc(rove_state_baseline.board_bytes),malloc(rove_state_candidate.board_bytes)};
    assert(p.baseline&&p.candidate);return p;
}
static void initial_pair(Pair *p){
    rove_state_baseline.initial(p->baseline);rove_state_candidate.initial(p->candidate);
}
static void fen_pair(Pair *p,const char *fen){
    assert(rove_state_baseline.fixture_fen(p->baseline,fen));
    assert(rove_state_candidate.fixture_fen(p->candidate,fen));
}
static int unsigned_compare(const void *a,const void *b){
    unsigned x=*(const unsigned *)a,y=*(const unsigned *)b;
    return (x>y)-(x<y);
}
static int visit(Pair *p,Pair *scratch,unsigned *legal){
    RoveStateSnapshot before=compare_position(p),after_a,after_b;
    unsigned a[MAX_MOVES],b[MAX_MOVES],legal_b[MAX_MOVES];
    int na=rove_state_baseline.generate(p->baseline,a),nb=rove_state_candidate.generate(p->candidate,b),count=0;
    assert(na>=0&&na<=MAX_MOVES&&na==nb);
    assert(!memcmp(a,b,(size_t)na*sizeof *a));
    pseudo_moves+=(unsigned)na;
    for(int i=0;i<na;i++){
        int accepted_a=rove_state_baseline.play(p->baseline,a[i],scratch->baseline);
        int accepted_b=rove_state_candidate.play(p->candidate,b[i],scratch->candidate);
        assert(accepted_a==accepted_b);
        if(accepted_a){
            compare_position(scratch);
            legal[count]=a[i];legal_b[count++]=b[i];legal_children++;
        }
    }
    qsort(legal,(size_t)count,sizeof *legal,unsigned_compare);
    qsort(legal_b,(size_t)count,sizeof *legal_b,unsigned_compare);
    assert(!memcmp(legal,legal_b,(size_t)count*sizeof *legal));
    for(int i=0;i<count;i++){hash_word(0,legal[i],4);hash_word(1,legal_b[i],4);}
    rove_state_baseline.snapshot(p->baseline,&after_a);rove_state_candidate.snapshot(p->candidate,&after_b);
    equal_snapshot(&before,&after_a);equal_snapshot(&before,&after_b);
    assert(rove_state_baseline.cached_white(p->baseline)==reference_scalar(&before));
    return count;
}
static void advance(Pair *p,Pair *scratch,unsigned move){
    assert(rove_state_baseline.play(p->baseline,move,scratch->baseline));
    assert(rove_state_candidate.play(p->candidate,move,scratch->candidate));
    Pair old=*p;*p=*scratch;*scratch=old;
    compare_position(p);
}
static void text_move(Pair *p,Pair *scratch,const char *text){
    unsigned from=(unsigned)(text[0]-'a')+(unsigned)(text[1]-'1')*16;
    unsigned to=(unsigned)(text[2]-'a')+(unsigned)(text[3]-'1')*16,promotion=0;
    if(text[4]){
        const char *names="  nbrq",*found=strchr(names,text[4]);assert(found);promotion=(unsigned)(found-names);
    }
    unsigned wanted=from|(to<<7)|(promotion<<14),legal[MAX_MOVES];
    int count=visit(p,scratch,legal),found=0;
    for(int i=0;i<count;i++)found|=legal[i]==wanted;
    assert(found);advance(p,scratch,wanted);
}
int main(void){
    assert(sizeof(int)==4&&sizeof(uint64_t)==8);
    assert(rove_state_baseline.board_bytes==176&&rove_state_candidate.board_bytes==168);
    assert(rove_state_baseline.cached_white&&!rove_state_candidate.cached_white);
    for(int v=-6;v<=6;v++)for(int sq=0;sq<64;sq++){
        int q=sq/8*16+sq%8,expected=reference_value(v,q);
        assert(abs(expected)<=910);
        assert(rove_state_baseline.piece_value(v,q)==expected&&rove_state_candidate.piece_value(v,q)==expected);
        assert(rove_state_baseline.table_term(v,sq)==expected&&rove_state_candidate.table_term(v,sq)==expected);
    }
    Pair p=allocate_pair(),scratch=allocate_pair();unsigned legal[MAX_MOVES];
    struct Fixture {const char *name,*fen;int dead,ep,legal;} fixtures[]={
        {"castles","r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",0,-1,-1},
        {"legal EP","6k1/8/8/3pP3/8/8/8/6K1 w - d6 0 1",0,83,-1},
        {"pinned EP","k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",0,-1,-1},
        {"uncapturable EP","6k1/8/8/3p4/8/8/8/6K1 w - d6 0 1",0,-1,-1},
        {"white promotions","4k2r/6P1/8/8/8/8/8/4K3 w - - 0 1",0,-1,-1},
        {"black promotions","4k3/8/8/8/8/8/1p6/R3K3 b - - 0 1",0,-1,-1},
        {"kiwipete","r3k2r/p1ppqpb1/bn2pnp1/2pP4/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1",0,-1,-1},
        {"mate","7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",0,-1,0},
        {"stalemate","7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",0,-1,0},
        {"kings","7k/8/8/8/8/8/8/K7 w - - 0 1",1,-1,-1},
        {"minor","7k/8/8/8/8/8/1B6/K7 w - - 0 1",1,-1,-1},
        {"two knights","7k/8/8/8/8/8/1NN5/K7 w - - 0 1",0,-1,-1},
        {"same bishops","7k/8/5b2/8/8/8/1B6/K7 w - - 0 1",1,-1,-1},
        {"opposite bishops","7k/8/8/5b2/8/8/1B6/K7 w - - 0 1",0,-1,-1}
    };
    for(size_t i=0;i<sizeof fixtures/sizeof *fixtures;i++){
        fen_pair(&p,fixtures[i].fen);RoveStateSnapshot s=compare_position(&p);
        assert(s.ep==fixtures[i].ep);
        assert(rove_state_baseline.dead_position(p.baseline)==fixtures[i].dead);
        int count=visit(&p,&scratch,legal);
        assert(fixtures[i].legal<0||count==fixtures[i].legal);
    }
    /* The signed white leaf must not change when only side-to-move changes. */
    fen_pair(&p,"8/7k/8/8/8/8/1Q6/K7 w - - 0 1");compare_position(&p);
    int white=rove_state_candidate.raw(p.candidate);
    fen_pair(&p,"8/7k/8/8/8/8/1Q6/K7 b - - 0 1");compare_position(&p);
    assert(rove_state_candidate.raw(p.candidate)==white);
    /* Same board/side/repetition key, different halfmove TT contexts. This
     * checks exact key fields/formula, not a forced production cutoff/miss. */
    const char *halves[]={
        "8/7k/8/8/8/8/1Q6/K7 w - - 0 1",
        "8/7k/8/8/8/8/1Q6/K7 w - - 99 1",
        "8/7k/8/8/8/8/1Q6/K7 w - - 100 1"
    };
    uint64_t half_keys[3],board_hash=0;
    for(int i=0;i<3;i++){
        fen_pair(&p,halves[i]);RoveStateSnapshot s=compare_position(&p);
        if(!i)board_hash=s.hash;else assert(s.hash==board_hash);
        half_keys[i]=rove_state_candidate.tt_key(p.candidate);
    }
    assert(half_keys[0]!=half_keys[1]&&half_keys[0]!=half_keys[2]&&half_keys[1]!=half_keys[2]);
    initial_pair(&p);RoveStateSnapshot original=compare_position(&p);
    const char *cycle[]={"g1f3","g8f6","f3g1","f6g8"};
    for(int round=0;round<2;round++){
        for(int i=0;i<4;i++)text_move(&p,&scratch,cycle[i]);
        RoveStateSnapshot s=compare_position(&p);
        assert(s.hash==original.hash&&s.halfmove==4*(round+1)&&s.reversible!=original.reversible);
    }
    RoveStateSnapshot path=compare_position(&p);uint64_t path_key=rove_state_candidate.tt_key(p.candidate);
    fen_pair(&p,"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 8 1");
    RoveStateSnapshot fresh=compare_position(&p);
    assert(path.hash==fresh.hash&&path.halfmove==fresh.halfmove&&path.reversible!=fresh.reversible);
    assert(path_key!=rove_state_candidate.tt_key(p.candidate));
    initial_pair(&p);
    for(int step=0;step<RANDOM_PLIES;step++){
        int count=visit(&p,&scratch,legal);RoveStateSnapshot s;
        rove_state_candidate.snapshot(p.candidate,&s);
        if(!count||s.halfmove>=90||step%127==126){initial_pair(&p);continue;}
        advance(&p,&scratch,legal[random_number()%(unsigned)count]);
    }
    assert(digest[0]==digest[1]);
    printf("{\"passed\":true,\"profile\":\"actual DEV=0 board/SIMD state only\",\"baseline_board_bytes\":176,\"candidate_board_bytes\":168,\"table_terms\":832,\"fixed_fixtures\":%zu,\"random_plies\":%d,\"positions\":%" PRIu64 ",\"legal_children\":%" PRIu64 ",\"pseudo_moves\":%" PRIu64 ",\"normalized_fnv1a64\":\"%016" PRIx64 "\",\"halfmove_and_path_context\":true,\"scalar_SIMD_equal\":true,\"parent_boards_unchanged\":true,\"production_TT_cutoff_claim\":false}\n",
        sizeof fixtures/sizeof *fixtures,RANDOM_PLIES,positions,legal_children,pseudo_moves,digest[0]);
    free(p.baseline);free(p.candidate);free(scratch.baseline);free(scratch.candidate);
    return 0;
}
