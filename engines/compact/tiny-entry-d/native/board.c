#include "tiny.h"
#include "hq.h"

/* D retains a readable mailbox as its authoritative position. Actual slider
 * attacks and generation use the selected scalar/HQ occupancy adapter. */
static const int steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};
#include "rove-common/board/mix"
int value(int v,int q){
    static const int material[7]={24576,48228,98624,65866,27124,41860,0};
    int a=material[abs(v)],rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=(a&1023)+advance*((a>>10)&7)+
        center*((a>>13)-3);
    return v>0?score:-score;
}
#include "rove-common/board/piece"
#include "rove-common/board/state"
#include "rove-common/board/put_scalar"
static int walk(const Board *,Move *,int,int);
#include "rove-common/move/attacked"
int dead(const Board *p){
    int state=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){if(state)return 0;state=-1;}
        else if(a==3){
            if(state<0)return 0;
            state|=1<<((q+(q>>4))&1);
            if(state==3)return 0;
        }
        else if(a&&a<6)return 0;
    }
    return 1;
}
/* Canonicalize EP before storing a position: an uncapturable target, including
 * one whose capture exposes the king, must not distinguish repetition keys. */
static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t;if(make(p,MOVE(q,p->e,0),&t))return;
        }
    }
    p->e=-1;
}
#include "rove-common/board/rights"
/* Internal contract: p came from start/FEN/a prior successful make, and m
 * belongs to gen(p). Both runtimes parse through gen+make; search, perft and
 * fallback only apply list members (a TT move only changes their ordering).
 * Thus gen proves valid endpoints, side/occupancy, pawn promotion geometry,
 * and the castle origin/transit safety. start/FEN plus rights(from)|rights(to) prove
 * the castle rook exists; normalized EP proves its captured pawn exists.
 * Keep the king-capture prohibition: gen includes attacked king squares.
 * Keep the resulting own-king test: ordinary pins, EP discoveries and castle
 * destination attacks are intentionally filtered only after applying a move.
 * ep may also request a boolean-only trial from a provisional parent: valid
 * side/king, empty target on the EP rank, opposing victim, and adjacent own
 * pawn prove a nonpromoting EP capture. Its h/r may be unfinished. Discard
 * the child; legality reads no h/r/v, and its e=-1 ends nested ep immediately. */
#include "rove-common/move/make"
static void add(Move *moves,int *n,int from,int to,int kind){
    int promotion=kind>1&&((to>>4)==0||(to>>4)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z)|((kind&1)<<3);
    }
}
/* Both modes walk forward from pieces of side s. A null output list asks
 * whether any geometric attack reaches sq, even if sq holds a friendly piece.
 * Pawn pushes and castling belong only to move generation, never attacks. */
static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    uint64_t occupied=d_occupancy(p->b);
    for(int from=0;from<128;from++){
        if(from&0x88){from+=7;continue;}
        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;
        if(a>=3&&a<=5){
            uint64_t destinations=d_sliding(occupied,(unsigned)from,(unsigned)a);
            while(destinations){
                int bit=__builtin_ctzll(destinations),to=(bit&7)+(bit>>3)*16;
                destinations&=destinations-1;
                if(!moves&&to==sq)return 1;
                if(moves&&p->b[to]*s<=0)add(moves,&n,from,to,!!p->b[to]);
            }
            continue;
        }
        if(moves&&a==1){
            int to=from+s*16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,2);
                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);
            }
        }
        int first=a==1?(s>0?12:14):a==2?0:8;
        int last=a==1?first+2:a==2?8:16;
        for(int i=first;i<last;i++){
            int to=from+steps[i];if(to&0x88)continue;
            int target=p->b[to];
            if(!moves&&to==sq)return 1;
            if(target*s>0||(moves&&a==1&&!target&&to!=p->e))continue;
            if(moves)add(moves,&n,from,to,a==1?3:!!target);
        }
        if(moves&&a==6){
            int home=s>0?4:116,shift=s>0?0:2;
            if(from==home&&!attacked(p,home,-s)){
                for(int d=1;d>=-1;d-=2)
                    if((p->c&((d>0?1:2)<<shift))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);
                }
        }
    }
    return n;
}
#include "rove-common/move/gen"
#include "rove-common/board/start"
#if DEV
#include "rove-common/board/fen"
int verify_board(const Board *p){
    if((p->s!=1&&p->s!=-1)||p->c<0||p->c>15||p->half<0||p->e<-1)return 0;
    Board t={0};t.s=p->s;t.c=p->c;t.e=p->e;t.k[0]=t.k[1]=-1;int kings[2]={0},counts[2]={0};
    for(int q=0;q<128;q++){
        int v=p->b[q];if(abs(v)>6||((q&0x88)&&v))return 0;
        if(v){if(++counts[v<0]>16)return 0;put(&t,q,v);if(abs(v)==6)kings[v<0]++;}
    }
    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v)return 0;
    for(int i=0;i<4;i++)if(t.c&(1<<i)){
        int home=i<2?4:116,rook=(i&1)?home-4:home+3,side=i<2?1:-1;
        if(t.b[home]!=side*6||t.b[rook]!=side*4)return 0;
    }
    if(t.e>=0&&((t.e&0x88)||(t.e>>4)!=(t.s>0?5:2)||t.b[t.e]||t.b[t.e-t.s*16]!=-t.s))return 0;
    ep(&t);return t.e==p->e&&p->h==(t.h^state(&t));
}
#endif
