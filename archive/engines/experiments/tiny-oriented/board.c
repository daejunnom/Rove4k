#include "tiny.h"
#if DEV
#include <ctype.h>
#include <errno.h>
#endif

/* A's mailbox is the only board representation. No bitboard or hash table
 * initialization is required. Piece and state key domains do not overlap. */
static const int steps[16]={33,31,18,14,-14,-18,-31,-33,1,-1,16,-16,17,15,-15,-17};
uint64_t mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
int value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[a]+advance*(a==1?7:a==4?2:0)+
        center*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
    return v>0?score:-score;
}
/* One canonical actual-colour hash is sufficient. Local negative pieces are
 * opponents; s maps both their sign and square back to the absolute board.
 * Piece keys stay in the original domain [0,1655], state in [2048,2072]. */
static uint64_t piece(const Board *p,int v,int q){return mix((uint64_t)((q^(p->s<0?112:0))+(v*p->s+6)*128));}
static int rotate(int c){return ((c&3)<<2)|(c>>2);}
static uint64_t state(const Board *p){
    return mix(2048+(p->s<0?rotate(p->c):p->c))^(p->s<0?mix(2064):0)^
        (p->e<0?0:mix(2065+(p->e&7)));
}
static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old){p->h^=piece(p,old,q);p->v-=value(old,q);}
    p->b[q]=(int8_t)v;
    if(v){p->h^=piece(p,v,q);p->v+=value(v,q);if(abs(v)==6)p->k[v<0]=q;}
}
/* h contains pieces only at both call sites. Flipping preserves their actual
 * placement; only the later state() attachment changes the actual turn key.
 * value(-v,q^112)==-value(v,q), so the relative HCE changes sign exactly. */
static void flip(Board *p){
    for(int q=0;q<64;q++){int v=p->b[q];p->b[q]=(int8_t)-p->b[q^112];p->b[q^112]=(int8_t)-v;}
    int king=p->k[0];p->k[0]=p->k[1]^112;p->k[1]=king^112;
    p->c=rotate(p->c);if(p->e>=0)p->e^=112;p->v=-p->v;p->s=-p->s;
}
static int walk(const Board *,Move *,int);
int attacked(const Board *p,int sq){return walk(p,0,sq);}
int dead(const Board *p){
    int minors=0,knights=0,colors=0;
    for(int q=0;q<128;q++)if(!(q&0x88)){
        int a=abs(p->b[q]);
        if(a==2){minors++;knights++;}
        else if(a==3){minors++;colors|=1<<((q+(q>>4))&1);}
        else if(a&&a<6)return 0;
    }
    return minors<2||(!knights&&colors!=3);
}
/* Canonicalize EP before storing a position: an uncapturable target, including
 * one whose capture exposes the king, must not distinguish repetition keys. */
static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-16+d;
        if(!(q&0x88)&&p->b[q]==1){
            Board t=*p;t.b[q]=t.b[p->e-16]=0;t.b[p->e]=1;
            if(!attacked(&t,p->k[0]))return;
        }
    }
    p->e=-1;
}
static int rights(int q){return q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}
/* Internal contract: p came from start/FEN/a prior successful make, and m
 * belongs to gen(p). Both runtimes parse through gen+make; search, perft and
 * fallback only apply list members (a TT move only changes their ordering).
 * Thus gen proves valid endpoints, side/occupancy, pawn promotion geometry,
 * and the castle origin/transit safety. start/FEN plus rights(from)|rights(to) prove
 * the castle rook exists; normalized EP proves its captured pawn exists.
 * Keep the king-capture prohibition: gen includes attacked king squares.
 * Keep the resulting own-king test: ordinary pins, EP discoveries and castle
 * destination attacks are intentionally filtered only after applying a move. */
int make(const Board *p,Move m,Board *t){
    int from=FROM(m),to=TO(m),prom=PROMO(m);
    int v=p->b[from],target=p->b[to];
    if(target==-6)return 0;
    *t=*p;t->h^=state(p);t->half++;t->e=-1;
    if(v==1){
        t->half=0;
        if(to==p->e&&!target)put(t,to-16,0);
        if(to-from==32)t->e=from+16;
        if(prom)v=prom;
    }
    if(target)t->half=0;
    if(v==6&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        put(t,rook,0);put(t,transit,4);
    }
    put(t,from,0);put(t,to,v);t->c&=~(rights(from)|rights(to));
    if(attacked(t,t->k[0]))return 0;
    flip(t);ep(t);t->h^=state(t);
    /* TT context retains the ordered reversible path. A pawn move or capture
     * resets it; repeated boards reached along distinct paths stay distinct. */
    t->r=t->half?((p->r<<1)|(p->r>>63))^t->h:t->h;
    return 1;
}
static void add(Move *moves,int *n,int from,int to,int pawn){
    int promotion=pawn&&(to>>4)==7;
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z);
    }
}
/* Both modes walk forward: own positive pieces for moves, negative for attacks.
 * A null output list asks
 * whether any geometric attack reaches sq, even if sq holds a friendly piece.
 * Pawn pushes and castling belong only to move generation, never attacks. */
static int walk(const Board *p,Move *moves,int sq){
    int n=0,s=moves?1:-1;
    for(int from=0;from<128;from++){
        if(from&0x88){from+=7;continue;}
        int a=p->b[from]*s;if(a<=0)continue;
        if(moves&&a==1){
            int to=from+16;
            if(!(to&0x88)&&!p->b[to]){
                add(moves,&n,from,to,1);
                if((from>>4)==1&&!p->b[to+16])add(moves,&n,from,to+16,0);
            }
        }
        int first=a==1?(moves?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int d=steps[i];
            for(int to=from+d;!(to&0x88);to+=d){
                int target=p->b[to];
                if(!moves&&to==sq)return 1;
                if(target*s>0||(moves&&a==1&&!target&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
        if(moves&&a==6){
            if(from==4&&!attacked(p,4)){
                if((p->c&1)&&!p->b[5]&&!p->b[6]&&!attacked(p,5))add(moves,&n,from,6,0);
                if((p->c&2)&&!p->b[3]&&!p->b[2]&&!p->b[1]&&!attacked(p,3))add(moves,&n,from,2,0);
                }
        }
    }
    return n;
}
int gen(const Board *p,Move *moves){return walk(p,moves,0);}
void start(Board *p){
    static const int back[8]={4,2,3,5,6,3,2,4};
    Board t={0};t.s=1;t.c=15;t.e=-1;
    for(int f=0;f<8;f++){put(&t,f,back[f]);put(&t,16+f,1);put(&t,96+f,-1);put(&t,112+f,-back[f]);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
#if DEV
int fen(Board *p,const char *s){
    static const char letters[]=" PNBRQK",castles[]="KQkq";
    Board t={0};int rank=7,file=0,kings[2]={0},counts[2]={0};t.s=1;t.e=-1;
    while(*s&&*s!=' '){
        int ch=(unsigned char)*s++;
        if(ch=='/'){if(file!=8||!rank)return 0;rank--;file=0;}
        else if(ch>='1'&&ch<='8'){file+=ch-'0';if(file>8)return 0;}
        else{
            const char *x=strchr(letters,toupper(ch));if(!x||x==letters||file>=8)return 0;
            int v=(int)(x-letters)*(isupper(ch)?1:-1);
            if(++counts[v<0]>16)return 0;
            if(abs(v)==6&&++kings[v<0]>1)return 0;
            put(&t,rank*16+file++,v);
        }
    }
    if(rank||file!=8||kings[0]!=1||kings[1]!=1||*s!=' ')return 0;
    s++;
    if(*s!='w'&&*s!='b')return 0;
    int side=*s++=='w'?1:-1;
    if(*s!=' ')return 0;
    s++;
    if(*s=='-')s++;
    else while(*s&&*s!=' '){const char *x=strchr(castles,*s++);if(!x)return 0;int b=1<<(x-castles);if(t.c&b)return 0;t.c|=b;}
    if(*s!=' ')return 0;
    s++;
    if(*s=='-')s++;
    else{
        if(!s[0]||!s[1])return 0;
        int f=s[0]-'a',r=s[1]-'1';
        if(f<0||f>7||r!=(side>0?5:2))return 0;
        t.e=r*16+f;s+=2;
        if(t.b[t.e]||t.b[t.e-side*16]!=-side)return 0;
    }
    for(int i=0;i<2;i++){
        if(*s!=' ')return 0;
        char *end;errno=0;long n=strtol(++s,&end,10);
        if(errno||end==s||n<(i?1:0)||n>1000000)return 0;
        if(!i)t.half=(int)n;
        s=end;
    }
    while(*s==' ')s++;
    if(*s)return 0;
    for(int i=0;i<4;i++){int home=i<2?4:116,rook=(i&1)?home-4:home+3,side=i<2?1:-1;if(t.b[home]!=side*6||t.b[rook]!=side*4)t.c&=~(1<<i);}
    if(side<0)flip(&t);
    ep(&t);t.h^=state(&t);t.r=t.h;*p=t;return 1;
}
int verify_board(const Board *p){
    if((p->s!=1&&p->s!=-1)||p->c<0||p->c>15||p->half<0||p->e<-1)return 0;
    Board t=*p;int found[2]={-1,-1},kings[2]={0},counts[2]={0},absolute_hce=0;uint64_t hash=0;
    for(int q=0;q<128;q++){
        int v=p->b[q];if(abs(v)>6||((q&0x88)&&v))return 0;
        if(v){
            if(++counts[v<0]>16)return 0;
            int actualq=q^(p->s<0?112:0),actualv=v*p->s;
            hash^=mix((uint64_t)(actualq+(actualv+6)*128));
            absolute_hce+=value(actualv,actualq);
            if(abs(v)==6){kings[v<0]++;found[v<0]=q;}
        }
    }
    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,found,sizeof found)||p->v!=absolute_hce*p->s)return 0;
    for(int i=0;i<4;i++)if(p->c&(1<<i)){
        int home=i<2?4:116,rook=(i&1)?home-4:home+3,side=i<2?1:-1;
        if(p->b[home]!=side*6||p->b[rook]!=side*4)return 0;
    }
    if(p->e>=0&&((p->e&0x88)||(p->e>>4)!=5||p->b[p->e]||p->b[p->e-16]!=-1))return 0;
    ep(&t);return t.e==p->e&&p->h==(hash^state(p));
}
#endif
