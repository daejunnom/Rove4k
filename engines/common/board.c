/* Shared mailbox state operations. Family-owned Board layouts, value() and
 * constants remain in their canonical templates. Assembly preserves every byte
 * inside each fragment; the framing comments are not emitted. */

/* rove:begin mix */
uint64_t mix(uint64_t x){
    x+=UINT64_C(0x9e3779b97f4a7c15);
    x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);
    x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);
    return x^(x>>31);
}
/* rove:end mix */

/* rove:begin piece */
static uint64_t piece(int v,int q){return mix((uint64_t)(q+(v+6)*128));}
/* rove:end piece */

/* rove:begin state */
static uint64_t state(const Board *p){
    return mix(2048+p->c)^(p->s<0?mix(2064):0)^
        (p->e<0?0:mix(2065+(p->e&7)));
}
/* rove:end state */

/* rove:begin put_scalar */
static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old){p->h^=piece(old,q);p->v-=value(old,q);}
    p->b[q]=(int8_t)v;
    if(v){p->h^=piece(v,q);p->v+=value(v,q);if(abs(v)==6)p->k[v<0]=q;}
}
/* rove:end put_scalar */

/* rove:begin put_dev_evaluation */
static void put(Board *p,int q,int v){
    int old=p->b[q];
    if(old){p->h^=piece(old,q);
#if DEV
p->v-=value(old,q);
#endif
}
    p->b[q]=(int8_t)v;
    if(v){p->h^=piece(v,q);
#if DEV
p->v+=value(v,q);
#endif
if(abs(v)==6)p->k[v<0]=q;}
}
/* rove:end put_dev_evaluation */

/* rove:begin rights */
static int rights(int q){return q==4?3:q==116?12:q==0?2:q==7?1:q==112?8:q==119?4:0;}
/* rove:end rights */

/* rove:begin start */
void start(Board *p){
    static const int back[8]={4,2,3,5,6,3,2,4};
    Board t={0};t.s=1;t.c=15;t.e=-1;
    for(int f=0;f<8;f++){put(&t,f,back[f]);put(&t,16+f,1);put(&t,96+f,-1);put(&t,112+f,-back[f]);}
    t.h^=state(&t);t.r=t.h;*p=t;
}
/* rove:end start */

/* rove:begin value_scalar */
int value(int v,int q){
    static const int material[7]={0,100,320,330,500,900,0};
    int a=abs(v),rank=q>>4,file=q&7,advance=v>0?rank:7-rank;
    int center=7-abs(2*file-7)-abs(2*rank-7);
    int score=material[a]+advance*(a==1?7:a==4?2:0)+
        center*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);
    return v>0?score:-score;
}
/* rove:end value_scalar */

/* rove:begin dead */
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
/* rove:end dead */

/* rove:begin ep */
static void ep(Board *p){
    if(p->e<0)return;
    for(int d=-1;d<=1;d+=2){
        int q=p->e-p->s*16+d;
        if(!(q&0x88)&&p->b[q]==p->s){
            Board t=*p;t.b[q]=t.b[p->e-p->s*16]=0;t.b[p->e]=(int8_t)p->s;
            if(!attacked(&t,p->k[p->s<0],-p->s))return;
        }
    }
    p->e=-1;
}
/* rove:end ep */

/* rove:begin fen */
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
    t.s=*s++=='w'?1:-1;
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
        if(f<0||f>7||r!=(t.s>0?5:2))return 0;
        t.e=r*16+f;s+=2;
        if(t.b[t.e]||t.b[t.e-t.s*16]!=-t.s)return 0;
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
    ep(&t);t.h^=state(&t);t.r=t.h;*p=t;return 1;
}
/* rove:end fen */
