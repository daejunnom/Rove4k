#include "rove.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <errno.h>

const int rove_value[7]={0,100,320,330,500,900,20000};
int hce_piece(int v,int q){int a=abs(v),r=q>>4,f=q&7,rr=v>0?r:7-r;int center=7-abs(2*f-7)-abs(2*r-7),score=a==6?0:rove_value[a];if(a==1)score+=rr*7+center*2;if(a==2)score+=center*9;if(a==3)score+=center*5;if(a==4)score+=rr*2;if(a==5)score+=center*2;if(a==6)score-=center*3;return v>0?score:-score;}
static uint64_t pieces[12][128], rights[16], eps[8], turn;
static const int knight[8]={33,31,18,14,-14,-18,-31,-33};
static const int rays[8]={1,-1,16,-16,17,15,-15,-17};
static const char letters[]=" PNBRQK";
static int color(int p){return p<0;}
static uint64_t bit(int q){return UINT64_C(1)<<((q>>4)*8+(q&7));}
static void put(Board *,int,int);
static uint64_t random64(uint64_t *s){uint64_t z=(*s+=UINT64_C(0x9e3779b97f4a7c15));z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);return z^(z>>31);}
void board_init(void){uint64_t s=UINT64_C(0x726f7665346b);for(int p=0;p<12;p++)for(int q=0;q<128;q++)pieces[p][q]=random64(&s);for(int i=0;i<16;i++)rights[i]=random64(&s);for(int i=0;i<8;i++)eps[i]=random64(&s);turn=random64(&s);}
#if ROVE_VARIANT == 4 && ROVE_HQ
static uint64_t reverse64(uint64_t x){x=((x>>1)&UINT64_C(0x5555555555555555))|((x&UINT64_C(0x5555555555555555))<<1);x=((x>>2)&UINT64_C(0x3333333333333333))|((x&UINT64_C(0x3333333333333333))<<2);x=((x>>4)&UINT64_C(0x0f0f0f0f0f0f0f0f))|((x&UINT64_C(0x0f0f0f0f0f0f0f0f))<<4);x=__builtin_bswap64(x);return x;}
static uint64_t hq(const Board *p,int sq,int direction){uint64_t mask=0,b=bit(sq),occ=p->occ[0]|p->occ[1];for(int s=-1;s<=1;s+=2)for(int q=sq+s*direction;!(q&0x88);q+=s*direction)mask|=bit(q);uint64_t line=occ&mask;return ((line-2*b)^reverse64(reverse64(line)-2*reverse64(b)))&mask;}
#endif
uint64_t attackers(const Board *p,int sq,int side){
    int c=side<0,d=side*16;uint64_t result=0;
    for(int a=-1;a<=1;a+=2){int q=sq-d+a;if(!(q&0x88))result|=p->bb[c][1]&bit(q);}
    for(int i=0;i<8;i++){int q=sq+knight[i];if(!(q&0x88))result|=p->bb[c][2]&bit(q);q=sq+rays[i];if(!(q&0x88))result|=p->bb[c][6]&bit(q);}
#if ROVE_VARIANT == 4 && ROVE_HQ
    uint64_t orth=hq(p,sq,1)|hq(p,sq,16),diag=hq(p,sq,15)|hq(p,sq,17);result|=orth&(p->bb[c][4]|p->bb[c][5]);result|=diag&(p->bb[c][3]|p->bb[c][5]);
#else
    uint64_t occ=p->occ[0]|p->occ[1];for(int i=0;i<8;i++)for(int q=sq+rays[i];!(q&0x88);q+=rays[i]){uint64_t b=bit(q);if(occ&b){result|=b&(p->bb[c][5]|p->bb[c][i<4?4:3]);break;}}
#endif
    return result;
}
int attacked(const Board *p,int sq,int side){
#if ROVE_VARIANT == 2 || ROVE_VARIANT == 4
    return attackers(p,sq,side)!=0;
#else
    int d=side*16;
    for(int a=-1;a<=1;a+=2){int q=sq-d+a;if(!(q&0x88)&&p->b[q]==side)return 1;}
    for(int i=0;i<8;i++){int q=sq+knight[i];if(!(q&0x88)&&p->b[q]==side*2)return 1;}
    for(int i=0;i<8;i++)for(int q=sq+rays[i],n=1;!(q&0x88);q+=rays[i],n++){
        int v=p->b[q];if(v){if(v*side>0){v=abs(v);if(v==5||(i<4&&v==4)||(i>=4&&v==3)||(n==1&&v==6))return 1;}break;}
    }
    return 0;
#endif
}
int in_check(const Board *p){return attacked(p,p->king[color(p->side)],-p->side);}
/* En passant enters a repetition key only if at least one legal capture exists. */
static int ep_file(const Board *p){
    if(p->ep<0)return -1;
    int d=p->side*16;
    for(int a=-1;a<=1;a+=2){int q=p->ep-d+a;if(!(q&0x88)&&p->b[q]==p->side){Board t=*p;put(&t,q,0);put(&t,p->ep-d,0);put(&t,p->ep,p->side);if(!attacked(&t,t.king[color(p->side)],-p->side))return p->ep&7;}}
    return -1;
}
uint64_t board_key(const Board *p){uint64_t h=rights[p->castle]^(p->side<0?turn:0);for(int q=0;q<128;q++){if(q&0x88){q+=7;continue;}int v=p->b[q];if(v)h^=pieces[(v>0?v-1:5-v)][q];}int e=ep_file(p);return e<0?h:h^eps[e];}
static void put(Board *p,int q,int v){
    int old=p->b[q];uint64_t mask=bit(q);
    if(old){int c=color(old),a=abs(old);uint64_t k=pieces[old>0?old-1:5-old][q];p->bb[c][a]^=mask;p->occ[c]^=mask;p->key^=k;p->hce-=hce_piece(old,q);if(a==1)p->pawnkey^=k;if(a!=6)p->material-=old>0?rove_value[a]:-rove_value[a];}
    p->b[q]=v;
    if(v){int c=color(v),a=abs(v);uint64_t k=pieces[v>0?v-1:5-v][q];p->bb[c][a]^=mask;p->occ[c]^=mask;p->key^=k;p->hce+=hce_piece(v,q);if(a==1)p->pawnkey^=k;if(a==6)p->king[c]=q;else p->material+=v>0?rove_value[a]:-rove_value[a];}
}
int board_fen(Board *p,const char *fen){
    Board t={0};t.side=1;t.ep=-1;t.full=1;t.king[0]=t.king[1]=-1;
    const char *s=fen;int rank=7,file=0,kings[2]={0};
    while(*s&&*s!=' '){char ch=*s++;if(ch=='/'){if(file!=8||rank==0)return 0;rank--;file=0;}else if(ch>='1'&&ch<='8'){file+=ch-'0';if(file>8)return 0;}else{const char *x=strchr(letters,toupper((unsigned char)ch));if(!x||x==letters||file>=8)return 0;int v=(int)(x-letters)*(isupper((unsigned char)ch)?1:-1);if(abs(v)==6&&++kings[color(v)]>1)return 0;put(&t,rank*16+file++,v);}}
    if(rank||file!=8||kings[0]!=1||kings[1]!=1||*s++!=' ')return 0;
    if(*s!='w'&&*s!='b')return 0;t.side=*s++=='w'?1:-1;if(*s++!=' ')return 0;
    if(*s=='-')s++;else{while(*s&&*s!=' '){const char *x=strchr("KQkq",*s++);if(!x)return 0;t.castle|=1<<(x-"KQkq");}}
    if(*s++!=' ')return 0;
    if(*s=='-')s++;else{if(!s[0]||!s[1])return 0;int f=s[0]-'a',r=s[1]-'1';if(f<0||f>7||(r!=2&&r!=5))return 0;t.ep=r*16+f;s+=2;if((t.side>0&&r!=5)||(t.side<0&&r!=2)||t.b[t.ep]||t.b[t.ep-t.side*16]!=-t.side)return 0;}
    if(*s==' '){char *end;errno=0;long half=strtol(s+1,&end,10);if(errno||end==s+1||half<0||half>1000000)return 0;t.half=(int)half;s=end;if(*s==' '){errno=0;long full=strtol(s+1,&end,10);if(errno||end==s+1||full<1||full>1000000)return 0;t.full=(int)full;s=end;}}
    while(*s==' ')s++;if(*s)return 0;
    if((t.castle&1)&&(t.b[4]!=6||t.b[7]!=4))t.castle&=~1;
    if((t.castle&2)&&(t.b[4]!=6||t.b[0]!=4))t.castle&=~2;
    if((t.castle&4)&&(t.b[116]!=-6||t.b[119]!=-4))t.castle&=~4;
    if((t.castle&8)&&(t.b[116]!=-6||t.b[112]!=-4))t.castle&=~8;
    t.key=board_key(&t);*p=t;return 1;
}
void board_start(Board *p){board_fen(p,"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");}
void board_format(const Board *p,char *out,int size){
    char b[128],*s=b;for(int r=7;r>=0;r--){int n=0;for(int f=0;f<8;f++){int v=p->b[r*16+f];if(!v)n++;else{if(n)*s++=(char)('0'+n);n=0;*s++=v>0?letters[v]:(char)tolower(letters[-v]);}}if(n)*s++=(char)('0'+n);if(r)*s++='/';}
    *s++=' ';*s++=p->side>0?'w':'b';*s++=' ';if(!p->castle)*s++='-';else for(int i=0;i<4;i++)if(p->castle&(1<<i))*s++="KQkq"[i];*s++=' ';if(p->ep<0)*s++='-';else{*s++=(char)('a'+(p->ep&7));*s++=(char)('1'+(p->ep>>4));}snprintf(s,(size_t)(b+sizeof b-s)," %d %d",p->half,p->full);snprintf(out,(size_t)size,"%s",b);
}
int make_move(const Board *p,unsigned m,Board *t){
    int from=FROM(m),to=TO(m),prom=PROM(m),v=p->b[from],target=p->b[to],side=p->side;
    if((from|to)&0x88||!v||v*side<0||target*side>0||abs(target)==6)return 0;
    *t=*p;int oldep=ep_file(p);t->key^=rights[t->castle]^(oldep<0?0:eps[oldep]);
    t->half++;t->ep=-1;if(side<0)t->full++;
    if(abs(v)==1){t->half=0;if(to==p->ep&&!target){if(p->b[to-side*16]!=-side)return 0;put(t,to-side*16,0);}if(abs(to-from)==32)t->ep=from+side*16;if((to>>4)==0||(to>>4)==7){if(prom<2||prom>5)return 0;v=prom*side;}else if(prom)return 0;}else if(prom)return 0;
    if(target)t->half=0;
    if(abs(v)==6&&abs(to-from)==2){int rfrom=to>from?from+3:from-4,rto=to>from?from+1:from-1;if(p->b[rfrom]!=side*4||in_check(p)||attacked(p,rto,-side))return 0;put(t,rfrom,0);put(t,rto,side*4);}
    put(t,from,0);put(t,to,v);
    if(from==4)t->castle&=~3;if(from==116)t->castle&=~12;
    if(from==0||to==0)t->castle&=~2;if(from==7||to==7)t->castle&=~1;
    if(from==112||to==112)t->castle&=~8;if(from==119||to==119)t->castle&=~4;
    t->side=-side;t->key^=turn^rights[t->castle];int e=ep_file(t);if(e>=0)t->key^=eps[e];
    return !attacked(t,t->king[color(side)],-side);
}
static void add(Move *m,int *n,int from,int to,int promotion){if(*n<MAXMOVES)m[(*n)++]=(Move){MOVE(from,to,promotion),0};}
int generate(const Board *p,Move *moves,int captures){
    int n=0,side=p->side;
    for(int from=0;from<128;from++){if(from&0x88){from+=7;continue;}int v=p->b[from];if(v*side<=0)continue;int a=abs(v);
        if(a==1){int to=from+side*16,last=(to>>4)==0||(to>>4)==7;
            if(!(to&0x88)&&!p->b[to]&&(!captures||last)){if(last)for(int z=2;z<=5;z++)add(moves,&n,from,to,z);else{add(moves,&n,from,to,0);int next=to+side*16;if((from>>4)==(side>0?1:6)&&!p->b[next])add(moves,&n,from,next,0);}}
            for(int d=-1;d<=1;d+=2){to=from+side*16+d;if(!(to&0x88)&&(p->b[to]*side<0||to==p->ep)){if((to>>4)==0||(to>>4)==7)for(int z=2;z<=5;z++)add(moves,&n,from,to,z);else add(moves,&n,from,to,0);}}
        }else if(a==2){for(int i=0;i<8;i++){int to=from+knight[i];if(!(to&0x88)&&p->b[to]*side<=0&&(!captures||p->b[to]))add(moves,&n,from,to,0);}}
        else{int first=a==3?4:0,last=a==4?4:8;for(int i=first;i<last;i++)for(int to=from+rays[i];!(to&0x88);to+=rays[i]){if(p->b[to]*side>0)break;if(!captures||p->b[to])add(moves,&n,from,to,0);if(p->b[to]||a==6)break;}
            if(a==6&&!captures){int home=side>0?4:116,shift=side>0?0:2;if(from==home&&!in_check(p)){if((p->castle&(1<<shift))&&!p->b[home+1]&&!p->b[home+2]&&!attacked(p,home+1,-side)&&!attacked(p,home+2,-side))add(moves,&n,from,home+2,0);if((p->castle&(2<<shift))&&!p->b[home-1]&&!p->b[home-2]&&!p->b[home-3]&&!attacked(p,home-1,-side)&&!attacked(p,home-2,-side))add(moves,&n,from,home-2,0);}}
        }
    }
    return n;
}
uint64_t perft(const Board *p,int depth){if(!depth)return 1;Move m[MAXMOVES];int n=generate(p,m,0);uint64_t nodes=0;for(int i=0;i<n;i++){Board t;if(make_move(p,m[i].m,&t))nodes+=perft(&t,depth-1);}return nodes;}
void move_string(unsigned m,char *s){if(!m){strcpy(s,"0000");return;}s[0]=(char)('a'+(FROM(m)&7));s[1]=(char)('1'+(FROM(m)>>4));s[2]=(char)('a'+(TO(m)&7));s[3]=(char)('1'+(TO(m)>>4));int p=PROM(m);s[4]=p?"  nbrq"[p]:0;s[5]=0;}
unsigned parse_move(const Board *p,const char *s){size_t len=strlen(s);if(len!=4&&len!=5)return 0;Move m[MAXMOVES];int n=generate(p,m,0);for(int i=0;i<n;i++){char b[8];move_string(m[i].m,b);if(!strcmp(s,b)){Board t;if(make_move(p,m[i].m,&t))return m[i].m;}}return 0;}
int board_invariant(const Board *p){Board t={0};t.king[0]=t.king[1]=-1;for(int q=0;q<128;q++){if(q&0x88){q+=7;continue;}if(p->b[q])put(&t,q,p->b[q]);}return p->key==board_key(p)&&p->pawnkey==t.pawnkey&&p->material==t.material&&p->hce==t.hce&&!memcmp(p->bb,t.bb,sizeof t.bb)&&!memcmp(p->occ,t.occ,sizeof t.occ)&&!memcmp(p->king,t.king,sizeof t.king);}
int drawn(const Board *p,const uint64_t *history,int n){
    if(p->half>=100)return 1;int count=0,start=n-1-p->half;if(start<0)start=0;for(int i=n-1;i>=start;i-=2)if(history[i]==p->key&&++count>=3)return 1;
    if(p->bb[0][1]|p->bb[1][1]|p->bb[0][4]|p->bb[1][4]|p->bb[0][5]|p->bb[1][5])return 0;
    int minors=0,knights=0,bishop_color=-1;for(int q=0;q<128;q++){if(q&0x88){q+=7;continue;}int a=abs(p->b[q]);if(a==2){minors++;knights++;}if(a==3){minors++;int c=((q>>4)+(q&7))&1;if(bishop_color==-1)bishop_color=c;else if(bishop_color!=c)bishop_color=2;}}
    return minors<=1||(!knights&&bishop_color<2);
}
