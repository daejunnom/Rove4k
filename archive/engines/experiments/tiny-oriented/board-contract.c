/* Independent board contract driver. Only the explicit build recipe includes
 * this test translation unit; it is never a submitted engine source. */
#include BOARD_SOURCE
#include <assert.h>
#define SQ(x,y) ((x)+16*(y))
#define X(q) ((q)&7)
#define Y(q) ((q)>>4)
#define KIND(v) abs(v)
#define COLOUR(v) ((v)<0)
#define TEAM(c) ((c)?-1:1)
#define CODE(a,c) ((a)*TEAM(c))
static uint64_t checks;
static int absolute_square(const Board *p,int q){
#if ORIENTED
    return q<0?-1:q^(p->s<0?112:0);
#else
    (void)p;return q;
#endif
}
static int actual_piece(const Board *p,int q){
#if ORIENTED
    return p->b[absolute_square(p,q)]*p->s;
#else
    return p->b[q];
#endif
}
static int actual_attack(const Board *p,int q,int colour){
#if ORIENTED
    if(TEAM(colour)==p->s){
        Board t=*p;flip(&t);return attacked(&t,absolute_square(&t,q));
    }
    return attacked(p,absolute_square(p,q));
#else
    return attacked(p,q,TEAM(colour));
#endif
}
static int reference_value(const Board *p){
    const int material[]={0,100,320,330,500,900,0};int result=0;
    for(int y=0;y<8;y++)for(int x=0;x<8;x++){
        int v=actual_piece(p,SQ(x,y)),a=KIND(v);if(!a)continue;
        int black=COLOUR(v),center=7-abs(2*x-7)-abs(2*y-7),score=material[a];
        switch(a){
            case 1:score+=7*(black?7-y:y)+2*center;break;
            case 2:score+=9*center;break;
            case 3:score+=5*center;break;
            case 4:score+=2*(black?7-y:y);break;
            case 5:score+=2*center;break;
            case 6:score-=3*center;break;
        }result+=black?-score:score;
    }return result;
}
static int reference_attack(const Board *p,int tx,int ty,int colour){
    for(int y=0;y<8;y++)for(int x=0;x<8;x++){
        int v=actual_piece(p,SQ(x,y)),a=KIND(v),dx=tx-x,dy=ty-y;
        if(!a||COLOUR(v)!=colour)continue;
        if(a==1&&dy==(colour?-1:1)&&abs(dx)==1)return 1;
        if(a==2&&abs(dx)*abs(dy)==2)return 1;
        if(a==6&&abs(dx)<=1&&abs(dy)<=1&&(dx||dy))return 1;
        if(a<3||a>5||(!dx&&!dy))continue;
        int diagonal=abs(dx)==abs(dy),straight=!dx||!dy;
        if(!((a==3&&diagonal)||(a==4&&straight)||(a==5&&(diagonal||straight))))continue;
        int sx=(dx>0)-(dx<0),sy=(dy>0)-(dy<0),px=x+sx,py=y+sy;
        for(;px!=tx||py!=ty;px+=sx,py+=sy)if(actual_piece(p,SQ(px,py)))break;
        if(px==tx&&py==ty)return 1;
    }return 0;
}
static void valid(const Board *p){
    assert(verify_board(p));
#if ORIENTED
    assert(reference_value(p)==p->v*p->s);
    Board twice=*p;flip(&twice);flip(&twice);assert(!memcmp(p,&twice,sizeof twice));
#else
    assert(reference_value(p)==p->v);
#endif
    checks++;
}
static void attack_audit(const Board *p){
    for(int y=0;y<8;y++)for(int x=0;x<8;x++)for(int c=0;c<2;c++)
        assert(actual_attack(p,SQ(x,y),c)==reference_attack(p,x,y,c));
}
static void text(const Board *p,Move m,char name[6]){
    int from=absolute_square(p,FROM(m)),to=absolute_square(p,TO(m));
    name[0]=(char)('a'+X(from));name[1]=(char)('1'+Y(from));
    name[2]=(char)('a'+X(to));name[3]=(char)('1'+Y(to));
    name[4]=PROMO(m)?"  nbrq"[PROMO(m)]:0;name[5]=0;
}
static void snapshot(const Board *p){
    static const char letters[]=" PNBRQK";valid(p);
    printf("{\"cells\":\"");
    for(int y=0;y<8;y++)for(int x=0;x<8;x++){
        int v=actual_piece(p,SQ(x,y)),a=KIND(v);char ch=a?letters[a]:'.';
        putchar(a&&COLOUR(v)?ch+'a'-'A':ch);
    }
    int castle=p->c,white=p->k[0],black=p->k[1],evaluation=p->v;
#if ORIENTED
    if(p->s<0){castle=rotate(castle);white=p->k[1];black=p->k[0];}
    evaluation*=p->s;
#endif
    printf("\",\"side\":%d,\"castle\":%d,\"ep\":%d,\"kings\":[%d,%d],\"half\":%d,\"v\":%d,\"h\":\"%016llx\",\"r\":\"%016llx\",\"dead\":%d}",
        p->s==TEAM(1),castle,absolute_square(p,p->e),absolute_square(p,white),absolute_square(p,black),p->half,evaluation,
        (unsigned long long)p->h,(unsigned long long)p->r,dead(p));
}
static void report(const Board *p){
    attack_audit(p);printf("{\"state\":");snapshot(p);printf(",\"attacks\":\"");
    for(int y=0;y<8;y++)for(int x=0;x<8;x++)for(int c=0;c<2;c++)putchar('0'+actual_attack(p,SQ(x,y),c));
    printf("\",\"pseudo\":[");Move moves[MOVES];int n=gen(p,moves);char name[6];
    for(int i=0;i<n;i++){text(p,moves[i],name);printf("%s\"%s\"",i?",":"",name);}
    printf("],\"children\":[");int emitted=0;
    for(int i=0;i<n;i++){
        Board t,before=*p;if(!make(p,moves[i],&t))continue;
        assert(!memcmp(p,&before,sizeof before));assert(t.r==(t.half?((p->r<<1)|(p->r>>63))^t.h:t.h));
        text(p,moves[i],name);printf("%s{\"move\":\"%s\",\"state\":",emitted++?",":"",name);snapshot(&t);putchar('}');
    }
    puts("]}");
}
static uint64_t perft(const Board *p,int depth){
    valid(p);if(!depth)return 1;Move moves[MOVES];int n=gen(p,moves);uint64_t total=0;
    for(int i=0;i<n;i++){Board t,before=*p;if(make(p,moves[i],&t)){
        assert(t.r==(t.half?((p->r<<1)|(p->r>>63))^t.h:t.h));total+=perft(&t,depth-1);
    }assert(!memcmp(p,&before,sizeof before));}return total;
}
static void random_attacks(void){
    Board p;start(&p);uint64_t r=UINT64_C(0x3ad90524c689e712);
    for(int sample=0;sample<1024;sample++){
        start(&p);
        for(int y=0;y<8;y++)for(int x=0;x<8;x++){
            r=r*UINT64_C(6364136223846793005)+1;int v=(r>>59)<10?(int)((r>>32)%13)-6:0;
            p.b[SQ(x,y)]=v?CODE(abs(v),v<0):0;
        }
#if ORIENTED
        if(sample&1)flip(&p);
#endif
        attack_audit(&p);
    }puts("{\"attack_queries\":131072}");
}
int main(int argc,char **argv){
    if(argc>1&&!strcmp(argv[1],"--overflow")){Move moves[MOVES];int n=MOVES;add(moves,&n,0,1,0);return 99;}
    Board p;start(&p);char line[4096];
    while(fgets(line,sizeof line,stdin)){
        line[strcspn(line,"\r\n")]=0;
        if(!strcmp(line,"start")){start(&p);printf("{\"ok\":true,\"state\":");snapshot(&p);puts("}");}
        else if(!strncmp(line,"fen ",4)){
            Board before=p;int ok=fen(&p,line+4);if(!ok)assert(!memcmp(&p,&before,sizeof p));
            printf("{\"ok\":%s,\"state\":",ok?"true":"false");snapshot(&p);puts("}");
        }else if(!strcmp(line,"report"))report(&p);
        else if(!strncmp(line,"play ",5)){
            Move moves[MOVES];int n=gen(&p,moves),ok=0;char name[6];
            for(int i=0;i<n;i++){text(&p,moves[i],name);if(!strcmp(name,line+5)){Board t;if(make(&p,moves[i],&t)){p=t;ok=1;}break;}}
            printf("{\"ok\":%s,\"state\":",ok?"true":"false");snapshot(&p);puts("}");
        }else if(!strncmp(line,"perft ",6)){
            int depth=atoi(line+6);assert(depth>=0&&depth<=5);checks=0;uint64_t nodes=perft(&p,depth);
            printf("{\"nodes\":%llu,\"checked\":%llu}\n",(unsigned long long)nodes,(unsigned long long)checks);
        }else if(!strcmp(line,"random-attacks"))random_attacks();
        else if(!strcmp(line,"inventory-invariant")){
            Board t=p;start(&t);put(&t,SQ(0,2),CODE(2,0));assert(!verify_board(&t));puts("{\"ok\":true}");
        }else if(!strcmp(line,"border-invariant")){
            Board t=p;
            t.b[8]=1;
            assert(!verify_board(&t));puts("{\"ok\":true}");
        }else if(!strcmp(line,"value-identity")){
            int count=0;for(int v=-6;v<=6;v++)if(v)for(int y=0;y<8;y++)for(int x=0;x<8;x++){
                int q=SQ(x,y);assert(value(-v,q^112)==-value(v,q));count++;
            }printf("{\"values\":%d}\n",count);
        }else if(!strcmp(line,"quit"))break;
        else assert(0);
        fflush(stdout);
    }
    return 0;
}
