#include "tiny.h"
#if DEV
#include <ctype.h>
#include <errno.h>
#endif

/* One 10x12 mailbox carries both the boundary and piece colours. From a real
 * square [21,98], the largest knight hop is 21, hence all probes are [0,119].
 * Every sliding ray stops at an EDGE cell before a second boundary step. */
static const int steps[16]={21,19,12,8,-8,-12,-19,-21,1,-1,10,-10,11,9,-9,-11};
uint64_t mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
int value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=TYPE(v),rank=RANK_OF(q),file=FILE_OF(q),advance=v&WHITE?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[a]+advance*(a==1?7:a==4?2:0)+
        center*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
    return v&WHITE?score:-score;
}
static uint64_t piece(int v,int q){
#if CONTROLLED
    /* Exactly the original 0x88 signed-piece domain, within [0,1655]. */
    return mix((uint64_t)(OLD_SQUARE(q)+((v&WHITE?TYPE(v):-TYPE(v))+6)*128));
#else
    /* Valid white keys are [1173,1890], black keys [2197,2914]. Neither
     * interval intersects the state domain [2048,2072]; EDGE is never hashed. */
    return mix((uint64_t)(q+v*128));
#endif
}
static uint64_t state(const Board *p){
    return mix(2048+p->c)^(p->s==BLACK?mix(2064):0)^
        (p->e<0?0:mix(2065+FILE_OF(p->e)));
}
static void blank(Board *p){
    memset(p,0,sizeof *p);memset(p->b,EDGE,sizeof p->b);
    for(int r=0;r<8;r++)memset(p->b+21+r*10,0,8);
    p->s=WHITE;p->e=-1;
}
static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old){p->h^=piece(old,q);p->v-=value(old,q);}
    p->b[q]=(uint8_t)v;
    if(v){p->h^=piece(v,q);p->v+=value(v,q);if(TYPE(v)==6)p->k[SIDE(v)]=q;}
}
static int walk(const Board *,Move *,int,int);
int attacked(const Board *p,int sq,int side){return walk(p,0,sq,side);}
int dead(const Board *p){
    int minors=0,knights=0,colors=0;
    for(int q=21;q<=98;q++){
        int a=TYPE(p->b[q]);
        if(a==2){minors++;knights++;}
        else if(a==3){minors++;colors|=1<<((FILE_OF(q)+RANK_OF(q))&1);}
        else if(a&&a<6)return 0;
    }
    return minors<2||(!knights&&colors!=3);
}
/* Only a legal EP capture distinguishes repetition positions. Border cells
 * have type zero and both colours, and cannot match the exact pawn code. */
static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-DIR(p->s)+d;
        if(p->b[q]==(p->s|1)){
            Board t=*p;t.b[q]=t.b[p->e-DIR(p->s)]=0;t.b[p->e]=(uint8_t)(p->s|1);
            if(!attacked(&t,p->k[SIDE(p->s)],OTHER(p->s)))return;
        }
    }
    p->e=-1;
}
static int rights(int q){return q==25?3:q==95?12:q==21?2:q==28?1:q==91?8:q==98?4:0;}
/* Contract: admitted start/FEN/prior legal make, and m is a current gen member.
 * gen proves real endpoints, colour/occupancy, promotions and castle origin/
 * transit safety. Admission and rights clearing prove a castle rook; normalized
 * EP proves its captured pawn. Keep target-king and resulting own-king tests. */
int make(const Board *p,Move m,Board *t){
    int from=FROM(m),to=TO(m),prom=PROMO(m),s=p->s,v=p->b[from],target=p->b[to];
    if(TYPE(target)==6)return 0;
    *t=*p;t->h^=state(p);t->half++;t->e=-1;
    if(TYPE(v)==1){
        t->half=0;
        if(to==p->e&&!target)put(t,to-DIR(s),0);
        if(abs(to-from)==20)t->e=from+DIR(s);
        if(prom)v=s|prom;
    }
    if(target)t->half=0;
    if(TYPE(v)==6&&abs(to-from)==2){
        int rook=to>from?from+3:from-4,transit=to>from?from+1:from-1;
        put(t,rook,0);put(t,transit,s|4);
    }
    put(t,from,0);put(t,to,v);t->c&=~(rights(from)|rights(to));t->s=OTHER(s);
    if(attacked(t,t->k[SIDE(s)],OTHER(s)))return 0;
    ep(t);t->h^=state(t);
    t->r=t->half?((p->r<<1)|(p->r>>63))^t->h:t->h;
    return 1;
}
static void add(Move *moves,int *n,int from,int to,int pawn){
    int promotion=pawn&&(RANK_OF(to)==0||RANK_OF(to)==7);
    for(int z=promotion?2:0;z<=(promotion?5:0);z++){
        if(*n>=MOVES)abort();
        moves[(*n)++]=MOVE(from,to,z);
    }
}
/* Both modes walk forward from pieces of colour s. Test an attack target
 * before friendly occupancy so an occupied friendly square can be protected.
 * EDGE&s merges friendly and boundary rejection without an offboard branch. */
static int walk(const Board *p,Move *moves,int sq,int s){
    int n=0;
    for(int from=21;from<=98;from++){
        int v=p->b[from],a=TYPE(v);if(!a||!(v&s))continue;
        if(moves&&a==1){
            int to=from+DIR(s);
            if(!p->b[to]){
                add(moves,&n,from,to,1);
                if(RANK_OF(from)==(s==WHITE?1:6)&&!p->b[to+DIR(s)])add(moves,&n,from,to+DIR(s),0);
            }
        }
        int first=a==1?(s==WHITE?12:14):a==2?0:a==3?12:8;
        int last=a==1?first+2:a==2?8:a==4?12:16;
        for(int i=first;i<last;i++){
            int d=steps[i];
            for(int to=from+d;;to+=d){
                int target=p->b[to];
                if(!moves&&to==sq)return 1;
                if((target&s)||(moves&&a==1&&!target&&to!=p->e))break;
                if(moves)add(moves,&n,from,to,a==1);
                if(target||a<3||a==6)break;
            }
        }
        if(moves&&a==6){
            int home=s==WHITE?25:95,shift=s==WHITE?0:2;
            if(from==home&&!attacked(p,home,OTHER(s))){
                if((p->c&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!attacked(p,home+1,OTHER(s)))add(moves,&n,from,home+2,0);
                if((p->c&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!attacked(p,home-1,OTHER(s)))add(moves,&n,from,home-2,0);
            }
        }
    }
    return n;
}
int gen(const Board *p,Move *moves){return walk(p,moves,0,p->s);}
void start(Board *p){
    static const int back[8]={4,2,3,5,6,3,2,4};
    Board t;blank(&t);t.c=15;
    for(int f=0;f<8;f++){put(&t,21+f,WHITE|back[f]);put(&t,31+f,WHITE|1);put(&t,81+f,BLACK|1);put(&t,91+f,BLACK|back[f]);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
#if DEV
int fen(Board *p,const char *s){
    static const char letters[]=" PNBRQK",castles[]="KQkq";
    Board t;blank(&t);int rank=7,file=0,kings[2]={0},counts[2]={0};
    while(*s&&*s!=' '){
        int ch=(unsigned char)*s++;
        if(ch=='/'){if(file!=8||!rank)return 0;rank--;file=0;}
        else if(ch>='1'&&ch<='8'){file+=ch-'0';if(file>8)return 0;}
        else{
            const char *x=strchr(letters,toupper(ch));if(!x||x==letters||file>=8)return 0;
            int v=(int)(x-letters)|(isupper(ch)?WHITE:BLACK);
            if(++counts[SIDE(v)]>16)return 0;
            if(TYPE(v)==6&&++kings[SIDE(v)]>1)return 0;
            put(&t,21+rank*10+file++,v);
        }
    }
    if(rank||file!=8||kings[0]!=1||kings[1]!=1||*s!=' ')return 0;
    s++;
    if(*s!='w'&&*s!='b')return 0;
    t.s=*s++=='w'?WHITE:BLACK;
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
        if(f<0||f>7||r!=(t.s==WHITE?5:2))return 0;
        t.e=21+r*10+f;s+=2;
        if(t.b[t.e]||t.b[t.e-DIR(t.s)]!=(OTHER(t.s)|1))return 0;
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
    for(int i=0;i<4;i++){int home=i<2?25:95,rook=(i&1)?home-4:home+3,side=i<2?WHITE:BLACK;if(t.b[home]!=(side|6)||t.b[rook]!=(side|4))t.c&=~(1<<i);}
    ep(&t);t.h^=state(&t);t.r=t.h;*p=t;return 1;
}
int verify_board(const Board *p){
    if((p->s!=WHITE&&p->s!=BLACK)||p->c<0||p->c>15||p->half<0||p->e<-1)return 0;
    Board t;blank(&t);t.s=p->s;t.c=p->c;t.e=p->e;t.k[0]=t.k[1]=-1;int kings[2]={0},counts[2]={0};
    for(int q=0;q<120;q++){
        int v=p->b[q],a=TYPE(v),color=v&~7;
        if(FILE_OF(q)<0||FILE_OF(q)>7||RANK_OF(q)<0||RANK_OF(q)>7){if(v!=EDGE)return 0;continue;}
        if(v&&(!a||a>6||(color!=WHITE&&color!=BLACK)))return 0;
        if(v){if(++counts[SIDE(v)]>16)return 0;put(&t,q,v);if(a==6)kings[SIDE(v)]++;}
    }
    if(kings[0]!=1||kings[1]!=1||memcmp(p->k,t.k,sizeof t.k)||p->v!=t.v)return 0;
    for(int i=0;i<4;i++)if(t.c&(1<<i)){
        int home=i<2?25:95,rook=(i&1)?home-4:home+3,side=i<2?WHITE:BLACK;
        if(t.b[home]!=(side|6)||t.b[rook]!=(side|4))return 0;
    }
    if(t.e>=0&&(FILE_OF(t.e)<0||FILE_OF(t.e)>7||RANK_OF(t.e)!=(t.s==WHITE?5:2)||t.b[t.e]||t.b[t.e-DIR(t.s)]!=(OTHER(t.s)|1)))return 0;
    ep(&t);return t.e==p->e&&p->h==(t.h^state(&t));
}
#endif