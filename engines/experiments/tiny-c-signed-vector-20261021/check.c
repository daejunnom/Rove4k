#define main omitted_engine_main
#ifdef CHECK_DEV
#include "dev.c"
typedef Board BT;
#define HALF half
#define PUT put
#define NORM_EP ep
#define STATE state
#define RAW tiny_raw
#define SEARCH search
#define CLEAR clear
#define NODES nodes
#define KEYS keys
#define LENGTH length
#else
#include "candidate-check.c"
typedef za BT;
#define HALF zL
#define PUT K
#define NORM_EP C
#define STATE R
#define RAW U
#define SEARCH P
#define CLEAR y
#define NODES z4
#define KEYS zQ
#define LENGTH zV
#endif
#undef main
#include <stddef.h>
#include <ctype.h>
#include <inttypes.h>
static unsigned scans,vector_calls,ordering_checks,scratch_checks,legal_total;
static unsigned captures,eps,castles,promotions[2],promotion_captures[2];
static void need(int good,const char *why){if(!good){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
static int low(int a,int b){return a<b?a:b;}
static int math_value(int v,int q){
 const int m[7]={0,100,320,330,500,900,0},a[7]={0,7,0,0,2,0,0},c[7]={0,2,9,5,0,2,-3};
 int k=abs(v),rank=q/16,file=q%16,center=2*(low(rank,7-rank)+low(file,7-file))-7;
 int n=m[k]+(v>0?rank:7-rank)*a[k]+center*c[k];return v>0?n:-n;
}
static uint64_t ref_mix(uint64_t n){n+=UINT64_C(0x9e3779b97f4a7c15);n=(n^(n>>30))*UINT64_C(0xbf58476d1ce4e5b9);n=(n^(n>>27))*UINT64_C(0x94d049bb133111eb);return n^(n>>31);}
static int scan(const BT *p){
 static const int material[7]={0,100,320,330,500,900,0},weights[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};
 int lanes[16]={0},net[8]={0},pieces[2]={0},score=0,dot=0,folded=0;
 uint64_t h=ref_mix(2048+p->c)^(p->s<0?ref_mix(2064):0)^(p->e<0?0:ref_mix(2065+(p->e&7)));
 for(int q=0;q<128;q++){
  int v=p->b[q];need(!(q&0x88)||v==0,"mailbox padding");if((q&0x88)||!v)continue;
  int k=abs(v),o=8*(v<0),term=math_value(v,q);need(k<=6,"piece domain");
  pieces[v<0]++;lanes[o+k-1]++;lanes[o+6]+=(v>0?term:-term)-material[k];score+=term;
  h^=ref_mix((uint64_t)(q+(v+6)*128));
 }
 need(pieces[0]<=16&&pieces[1]<=16,"population bound");need(p->h==h,"full independent hash rebuild");
 for(int i=0;i<16;i++){
  need(abs(lanes[i])<=1008,"feature bound");dot+=lanes[i]*weights[i];
 }
 need(lanes[7]==0&&lanes[15]==0&&dot==score,"independent old16 dot/scalar equality");
 for(int k=1;k<=6;k++)net[k]=lanes[k-1]-lanes[k+7];net[7]=lanes[6]-lanes[14];
 const int coefficients[8]={0,100,320,330,500,900,0,1};
 for(int k=0;k<8;k++){
  need(abs(net[k])<=(k==7?2016:16),"signed8 feature bounds");folded+=net[k]*coefficients[k];
#ifndef CHECK_DEV
  need(p->x[k]==net[k],"full independent signed8 rebuild");
#endif
 }
 need(folded==dot&&net[0]==0,"old16 to signed8 algebra and padding");
#ifdef CHECK_DEV
 need(p->v==score,"DEV independent incremental HCE");
#endif
 scans++;return score;
}
#ifndef CHECK_DEV
/* Only U's definition name is changed in the included fixture copy. Its body
 * is exact. P's existing U calls reach this independent checker then the body. */
static int U(const za *p){int expected=scan(p),actual=shipping_U(p);need(actual==expected,"actual SIMD/scalar");vector_calls++;return actual;}
#endif
static void check(const BT *p){int expected=scan(p);need(RAW(p)==expected,"actual raw evaluator");}
static void empty(BT *p){memset(p,0,sizeof *p);p->s=1;p->e=-1;p->h=STATE(p);}
static void load(BT *p,const char *text){
#ifdef CHECK_DEV
 need(fen(p,text),"reference FEN ingress");
#else
 char cells[96],side,rights[8],enpassant[3];int half,full;static const char letters[]=" PNBRQK",castle_flags[]="KQkq";
 need(sscanf(text,"%95s %c %7s %2s %d %d",cells,&side,rights,enpassant,&half,&full)==6,"fixture FEN fields");
 BT t={0};t.s=side=='w'?1:-1;t.e=-1;t.HALF=half;
 int rank=7,file=0;for(const char *c=cells;*c;c++){
  if(*c=='/'){rank--;file=0;}else if(isdigit((unsigned char)*c))file+=*c-'0';else{
   const char *k=strchr(letters,toupper((unsigned char)*c));need(k!=0,"fixture piece");
   PUT(&t,rank*16+file++,(int)(k-letters)*(isupper((unsigned char)*c)?1:-1));
  }
 }
 for(const char *c=rights;*c&&*c!='-';c++){const char *k=strchr(castle_flags,*c);need(k!=0,"fixture right");t.c|=1<<(k-castle_flags);}
 if(enpassant[0]!='-')t.e=(enpassant[1]-'1')*16+enpassant[0]-'a';
 NORM_EP(&t);t.h^=STATE(&t);t.r=t.h;*p=t;
#endif
 check(p);
}
static void children(const BT *p,int id){
 BT saved;memcpy(&saved,p,sizeof saved);Move list[MOVES];int n=gen(p,list),legal=0;uint64_t digest=0;
 check(p);
 for(int i=0;i<n;i++){
  BT child;if(!make(p,list[i],&child))continue;check(&child);legal++;legal_total++;
  need(memcmp(&saved,p,sizeof saved)==0,"const parent changed");
  uint64_t context=child.HALF?((p->r<<1)|(p->r>>63))^child.h:child.h;
  need(child.r==context&&child.s==-p->s,"reversible context and side");
  int from=FROM(list[i]),to=TO(list[i]),color=p->s<0,cap=p->b[to]!=0;
  if(cap)captures|=1u<<color;
  if(abs(p->b[from])==1&&to==p->e&&!p->b[to])eps|=1u<<color;
  if(abs(p->b[from])==6&&abs(to-from)==2)castles|=1u<<(color*2+(to<from));
  if(PROMO(list[i])){promotions[color]|=1u<<PROMO(list[i]);if(cap)promotion_captures[color]|=1u<<PROMO(list[i]);}
  digest=ref_mix(digest^child.h^child.r^((uint64_t)list[i]<<32)^(uint32_t)math_value(child.b[TO(list[i])],TO(list[i]))^(unsigned)child.HALF);
 }
 printf("{\"kind\":\"case\",\"id\":%d,\"legal\":%d,\"hash\":\"%016" PRIx64 "\",\"digest\":\"%016" PRIx64 "\",\"ep\":%d,\"half\":%d}\n",id,legal,p->h,digest,p->e,p->HALF);
}
static void scratch(const char *fen_text,int requested,int expected){
 BT p;load(&p,fen_text);p.e=requested;BT original=p,poisoned=p;
#ifndef CHECK_DEV
 for(int i=0;i<8;i++)poisoned.x[i]=(int16_t)(i&1?-30000:30000);
 int16_t before[8];memcpy(before,poisoned.x,sizeof before);
#else
 poisoned.v=123456789;
#endif
 NORM_EP(&original);NORM_EP(&poisoned);
 need(original.e==expected&&poisoned.e==expected,"attack-only EP result depends on cache");
 need(!memcmp(original.b,p.b,sizeof p.b)&&!memcmp(poisoned.b,p.b,sizeof p.b),"EP preserves parent mailbox");
#ifndef CHECK_DEV
 need(memcmp(before,poisoned.x,sizeof before)==0,"EP touched feature cache");
#else
 need(poisoned.v==123456789,"EP touched DEV cache");
#endif
 scratch_checks++;
}
static void search_check(int color){
 BT p;if(!color)start(&p);else load(&p,"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1");check(&p);
 CLEAR();memset(workers,0,sizeof workers);workers[0].LENGTH=1;workers[0].KEYS[0]=p.h;deadline=UINT64_MAX;atomic_store(&stopped,0);
 Move best=0;int score=SEARCH(workers,&p,2,-MATE,MATE,0,0,&best);need(!atomic_load(&stopped)&&workers[0].NODES>1,"positive actual search");
 Move list[MOVES];int n=gen(&p,list),found=0;for(int i=0;i<n;i++)if(list[i]==best){BT child;found=make(&p,best,&child);if(found)check(&child);}
 need(found,"search returned illegal move");
 printf("{\"kind\":\"search\",\"color\":%d,\"score\":%d,\"best\":%u,\"nodes\":%llu}\n",color,score,best,(unsigned long long)workers[0].NODES);
}
int main(void){
#ifdef CHECK_DEV
 need(sizeof(BT)==176&&offsetof(BT,h)==160,"actual DEV reference layout");
#else
 typedef struct{int8_t b[128];int16_t x[16];int s,c,e,k[2],zL;uint64_t h,r;}OldBoard;
 need(sizeof(OldBoard)==200&&offsetof(OldBoard,s)==160&&offsetof(OldBoard,h)==184&&offsetof(OldBoard,r)==192,"actual old16 shipping declaration layout");
 need(sizeof(BT)==184&&offsetof(BT,x)==128&&offsetof(BT,s)==144&&offsetof(BT,h)==168&&offsetof(BT,r)==176,"actual signed8 Board layout");
 printf("{\"kind\":\"layout\",\"old_size\":%zu,\"new_size\":%zu,\"x_offset\":%zu,\"side_offset\":%zu,\"hash_offset\":%zu,\"context_offset\":%zu}\n",sizeof(OldBoard),sizeof(BT),offsetof(BT,x),offsetof(BT,s),offsetof(BT,h),offsetof(BT,r));
#endif
 for(int v=-6;v<=6;v++)for(int q=0;q<128;q++)if(!(q&0x88)){
  need(value(v,q)==math_value(v,q),"independent piece value");BT p;empty(&p);PUT(&p,q,v);check(&p);
 }
 for(int k=1;k<=6;k++){
  BT p;empty(&p);for(int f=0;f<8;f++)for(int rank=0;rank<2;rank++){
   PUT(&p,rank*16+f,k);check(&p);PUT(&p,(rank+6)*16+f,-k);check(&p);
  }
 }
 for(int v=-6;v<=6;v++)for(int victim=-6;victim<=6;victim++)for(int q=0;q<128;q++)if(!(q&0x88)){
  BT p;empty(&p);int to=119-q;PUT(&p,q,v);PUT(&p,to,victim);
  int actual=500000+abs(value(p.b[to],to))*16-abs(value(p.b[q],q));
  int expected=500000+abs(math_value(victim,to))*16-abs(math_value(v,q));need(actual==expected,"capture ordering");ordering_checks++;
 }
 BT start_board;start(&start_board);children(&start_board,0);
#ifndef CHECK_DEV
 int original=shipping_U(&start_board);for(int i=0;i<8;i++){BT p=start_board;p.x[i]++;need(shipping_U(&p)==original+qm[i],"all signed8 SIMD lanes including zero king/padding");}
#endif
 const char *cases[]={
  "4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1","4k3/8/8/3p4/4P3/8/8/4K3 b - - 0 1",
  "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",
  "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/K3R3 b - d3 0 1",
  "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
  "1r5k/P7/8/8/8/8/8/7K w - - 0 1","7k/8/8/8/8/8/p7/1R5K b - - 0 1",
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 99 1"};
 for(unsigned i=0;i<sizeof cases/sizeof *cases;i++){BT p;load(&p,cases[i]);children(&p,(int)i+1);}
 scratch(cases[2],83,83);scratch(cases[3],35,35);scratch(cases[4],83,-1);scratch(cases[5],35,-1);
 need(captures==3&&eps==3&&castles==15,"both-color capture/EP/castle coverage");
 need(promotions[0]==60&&promotions[1]==60&&promotion_captures[0]==60&&promotion_captures[1]==60,"all four promotions both colors");
 table=calloc((size_t)1<<18,sizeof *table);need(table!=0,"fixture TT allocation");search_check(0);search_check(1);free(table);
 printf("{\"kind\":\"summary\",\"scans\":%u,\"actual_vector_checks\":%u,\"ordering_checks\":%u,\"scratch_checks\":%u,\"legal_children\":%u,\"pass\":true}\n",scans,vector_calls,ordering_checks,scratch_checks,legal_total);
 return 0;
}
