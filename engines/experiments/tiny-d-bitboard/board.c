#include "tiny.h"
#include "hq.h"

/* These eight bitboards are the complete position authority. No square array,
 * occupancy reconstruction, cached kings, or alternate coordinate space. */
uint64_t mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
int value(int kind,int q,int color){
    static const int material[6]={100,320,330,500,900,0};
    int rank=q>>3,file=q&7,advance=color?7-rank:rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[kind]+advance*(kind==0?7:kind==3?2:0)+
        center*(kind==1?9:kind==2?5:kind==5?-3:(kind==0||kind==4)*2);
    return color?-score:score;
}
static uint64_t state(const Board *p){
    return mix(2048+p->c)^(p->s?mix(2064):0)^(p->e<0?0:mix(2065+(p->e&7)));
}
static void toggle(Board *p,int kind,int q,int color){
    uint64_t b=UINT64_C(1)<<q;
    p->v+=(p->color[color]&b)?-value(kind,q,color):value(kind,q,color);
    p->pieces[kind]^=b;p->color[color]^=b;
    p->h^=mix(q+(kind+6*color)*64);
}
static uint64_t pawn(uint64_t b,int color){
    return color?((b&UINT64_C(0xfefefefefefefefe))>>9)|((b&UINT64_C(0x7f7f7f7f7f7f7f7f))>>7):
                 ((b&UINT64_C(0xfefefefefefefefe))<<7)|((b&UINT64_C(0x7f7f7f7f7f7f7f7f))<<9);
}
static uint64_t leaper(int q,int kind){
    uint64_t b=UINT64_C(1)<<q,l=b&UINT64_C(0xfefefefefefefefe),r=b&UINT64_C(0x7f7f7f7f7f7f7f7f);
    if(kind==5){b=l>>1|r<<1;b|=(b|(UINT64_C(1)<<q))<<8|(b|(UINT64_C(1)<<q))>>8;return b;}
    return (l<<15)|(l>>17)|(r<<17)|(r>>15)|
        ((b&UINT64_C(0xfcfcfcfcfcfcfcfc))<<6)|((b&UINT64_C(0xfcfcfcfcfcfcfcfc))>>10)|
        ((b&UINT64_C(0x3f3f3f3f3f3f3f3f))<<10)|((b&UINT64_C(0x3f3f3f3f3f3f3f3f))>>6);
}
int attacked(const Board *p,int sq,int color){
    uint64_t own=p->color[color],o=p->color[0]|p->color[1],b=UINT64_C(1)<<sq;
    return !!(own&((pawn(b,color^1)&p->pieces[0])|(leaper(sq,1)&p->pieces[1])|
        (leaper(sq,5)&p->pieces[5])|(d_sliding(o,(unsigned)sq,2)&(p->pieces[2]|p->pieces[4]))|
        (d_sliding(o,(unsigned)sq,3)&(p->pieces[3]|p->pieces[4]))));
}
int dead(const Board *p){
    if(p->pieces[0]|p->pieces[3]|p->pieces[4])return 0;
    uint64_t minors=p->pieces[1]|p->pieces[2],bishops=p->pieces[2];
    return !(minors&(minors-1))||(!p->pieces[1]&&
        (!(bishops&UINT64_C(0x55aa55aa55aa55aa))||!(bishops&UINT64_C(0xaa55aa55aa55aa55))));
}
static int king(const Board *p,int color){return __builtin_ctzll(p->pieces[5]&p->color[color]);}
/* EP belongs to the repetition key only when at least one capture is legal. */
static void ep(Board *p){
    if(p->e<0)return;
    uint64_t candidates=pawn(UINT64_C(1)<<p->e,p->s^1)&p->pieces[0]&p->color[p->s];
    while(candidates){
        int q=__builtin_ctzll(candidates);candidates&=candidates-1;
        Board t=*p;
        uint64_t from=UINT64_C(1)<<q,to=UINT64_C(1)<<p->e,
                 victim=UINT64_C(1)<<(p->e+(p->s?8:-8));
        t.color[p->s]^=from|to;t.color[p->s^1]^=victim;t.pieces[0]^=from|to|victim;
        if(!attacked(&t,king(&t,p->s),p->s^1))return;
    }
    p->e=-1;
}
static int rights(int q){return q==4?3:q==60?12:q==0?2:q==7?1:q==56?8:q==63?4:0;}
/* Caller supplies a gen member. Metadata is generated from the authoritative
 * bitboards; king captures remain forbidden and resulting king safety is
 * checked here for pins, EP discoveries and castling destinations. */
int make(const Board *p,Move m,Board *t){
    int from=FROM(m),to=TO(m),kind=KIND(m),capture=CAP(m),s=p->s,prom=PROMO(m);
    if(capture==6)return 0;
    *t=*p;t->h^=state(p);t->half++;t->e=-1;
    if(capture){
        int q=kind==0&&to==p->e?to+(s?8:-8):to;
        toggle(t,capture-1,q,s^1);t->half=0;
    }
    toggle(t,kind,from,s);
    if(kind==0){
        t->half=0;
        if(abs(to-from)==16)t->e=(to+from)/2;
    }
    toggle(t,prom?prom-1:kind,to,s);
    if(kind==5&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        toggle(t,3,rook,s);toggle(t,3,transit,s);
    }
    t->c&=~(rights(from)|rights(to));t->s^=1;
    if(attacked(t,king(t,s),s^1))return 0;
    ep(t);t->h^=state(t);t->r=t->half?((p->r<<1)|(p->r>>63))^t->h:t->h;return 1;
}
static int occupant(const Board *p,int to){
    uint64_t b=UINT64_C(1)<<to;
    for(int k=0;k<6;k++)if(p->pieces[k]&b)return k+1;
    return 0;
}
static void add(const Board *p,Move *moves,int *n,int from,int to,int kind){
    int promotion=kind==0&&(to<8||to>=56),capture=occupant(p,to);
    if(kind==0&&to==p->e)capture=1;
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z,kind,capture);
    }
}
int gen(const Board *p,Move *moves){
    int n=0,s=p->s;uint64_t o=p->color[0]|p->color[1];
    for(int kind=0;kind<6;kind++){
        uint64_t pieces=p->pieces[kind]&p->color[s];
        while(pieces){
            int from=__builtin_ctzll(pieces);pieces&=pieces-1;uint64_t destinations;
            if(!kind){
                int to=from+(s?-8:8);
                destinations=pawn(UINT64_C(1)<<from,s)&(p->color[s^1]|(p->e<0?0:UINT64_C(1)<<p->e));
                if(to>=0&&to<64&&!(o&(UINT64_C(1)<<to))){
                    destinations|=UINT64_C(1)<<to;
                    if((from>>3)==(s?6:1)&&!(o&(UINT64_C(1)<<(to+(s?-8:8)))))
                        destinations|=UINT64_C(1)<<(to+(s?-8:8));
                }
            }else destinations=(kind==1||kind==5?leaper(from,kind):d_sliding(o,(unsigned)from,(unsigned)kind))&~p->color[s];
            while(destinations){int to=__builtin_ctzll(destinations);destinations&=destinations-1;add(p,moves,&n,from,to,kind);}
            if(kind==5){
                int home=s?60:4,shift=s?2:0;
                if(from==home&&!attacked(p,home,s^1)){
                    if((p->c&(1<<shift))&&!(o&((UINT64_C(1)<<(home+1))|(UINT64_C(1)<<(home+2))))&&!attacked(p,home+1,s^1))add(p,moves,&n,from,home+2,kind);
                    if((p->c&(2<<shift))&&!(o&((UINT64_C(1)<<(home-1))|(UINT64_C(1)<<(home-2))|(UINT64_C(1)<<(home-3))))&&!attacked(p,home-1,s^1))add(p,moves,&n,from,home-2,kind);
                }
            }
        }
    }
    return n;
}
void start(Board *p){
    static const int back[8]={3,1,2,4,5,2,1,3};Board t={0};t.c=15;t.e=-1;
    for(int f=0;f<8;f++){toggle(&t,back[f],f,0);toggle(&t,0,8+f,0);toggle(&t,0,48+f,1);toggle(&t,back[f],56+f,1);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
#if DEV
static int count(uint64_t b){int n=0;while(b){b&=b-1;n++;}return n;}
int fen(Board *p,const char *s){
    static const char letters[]="PNBRQK",castles[]="KQkq";
    Board t={0};int rank=7,file=0,kings[2]={0},counts[2]={0};t.e=-1;
    while(*s&&*s!=' '){
        int ch=(unsigned char)*s++;
        if(ch=='/'){if(file!=8||!rank)return 0;rank--;file=0;}
        else if(ch>='1'&&ch<='8'){file+=ch-'0';if(file>8)return 0;}
        else{
            const char *x=strchr(letters,toupper(ch));if(!x||!*x||file>=8)return 0;
            int kind=(int)(x-letters),color=!isupper(ch);
            if(++counts[color]>16||(kind==5&&++kings[color]>1))return 0;
            toggle(&t,kind,rank*8+file++,color);
        }
    }
    if(rank||file!=8||kings[0]!=1||kings[1]!=1||*s!=' ')return 0;
    s++;if(*s!='w'&&*s!='b')return 0;t.s=*s++=='b';if(*s!=' ')return 0;s++;
    if(*s=='-')s++;
    else while(*s&&*s!=' '){const char *x=strchr(castles,*s++);if(!x||!*x)return 0;int b=1<<(x-castles);if(t.c&b)return 0;t.c|=b;}
    if(*s!=' ')return 0;s++;
    if(*s=='-')s++;
    else{
        if(!s[0]||!s[1])return 0;int f=s[0]-'a',r=s[1]-'1';
        if(f<0||f>7||r!=(t.s?2:5))return 0;t.e=r*8+f;s+=2;
        uint64_t b=UINT64_C(1)<<t.e,v=UINT64_C(1)<<(t.e+(t.s?8:-8));
        if(((t.color[0]|t.color[1])&b)||!(t.pieces[0]&t.color[t.s^1]&v))return 0;
    }
    for(int i=0;i<2;i++){
        if(*s!=' ')return 0;char *end;errno=0;long n=strtol(++s,&end,10);
        if(errno||end==s||n<(i?1:0)||n>1000000)return 0;if(!i)t.half=(int)n;s=end;
    }
    while(*s==' ')s++;if(*s)return 0;
    for(int i=0;i<4;i++){
        int home=i<2?4:60,rook=(i&1)?home-4:home+3,color=i>=2;
        if(!(t.pieces[5]&t.color[color]&(UINT64_C(1)<<home))||!(t.pieces[3]&t.color[color]&(UINT64_C(1)<<rook)))t.c&=~(1<<i);
    }
    ep(&t);t.h^=state(&t);t.r=t.h;*p=t;return 1;
}
int verify_board(const Board *p){
    if(p->s<0||p->s>1||p->c<0||p->c>15||p->half<0||p->e<-1||p->e>=64||(p->color[0]&p->color[1]))return 0;
    Board t={0};t.s=p->s;t.c=p->c;t.e=p->e;uint64_t all=0;
    for(int k=0;k<6;k++){
        if(all&p->pieces[k])return 0;all|=p->pieces[k];
        for(int c=0;c<2;c++){
            uint64_t pieces=p->pieces[k]&p->color[c];
            if(k==5&&count(pieces)!=1)return 0;
            while(pieces){int q=__builtin_ctzll(pieces);pieces&=pieces-1;toggle(&t,k,q,c);}
        }
    }
    if(all!=(p->color[0]|p->color[1])||count(p->color[0])>16||count(p->color[1])>16||t.v!=p->v)return 0;
    for(int i=0;i<4;i++)if(p->c&(1<<i)){
        int home=i<2?4:60,rook=(i&1)?home-4:home+3,color=i>=2;
        if(!(t.pieces[5]&t.color[color]&(UINT64_C(1)<<home))||!(t.pieces[3]&t.color[color]&(UINT64_C(1)<<rook)))return 0;
    }
    if(t.e>=0){
        if((t.e>>3)!=(t.s?2:5))return 0;
        uint64_t b=UINT64_C(1)<<t.e,v=UINT64_C(1)<<(t.e+(t.s?8:-8));
        if(((t.color[0]|t.color[1])&b)||!(t.pieces[0]&t.color[t.s^1]&v))return 0;
    }
    ep(&t);return t.e==p->e&&p->h==(t.h^state(&t));
}
#endif
