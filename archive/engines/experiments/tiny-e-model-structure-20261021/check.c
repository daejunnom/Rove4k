#define main omitted_engine_main
#include "candidate-check.c"
#undef main
#include <stddef.h>
#include <ctype.h>
#include <inttypes.h>
static unsigned scans,leaf_calls,order_calls,legal_total,captures,eps,castles,promotions[2],promotion_captures[2];
static void need(int good,const char *why){if(!good){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
static int low(int a,int b){return a<b?a:b;}
static int center(int q){return low(q%16,7-q%16)+low(q/16,7-q/16);}
static uint64_t hash_mix(uint64_t x){x+=UINT64_C(0x9e3779b97f4a7c15);x=(x^(x>>30))*UINT64_C(0xbf58476d1ce4e5b9);x=(x^(x>>27))*UINT64_C(0x94d049bb133111eb);return x^(x>>31);}
static int scalar(const za *p){
 const int material[7]={0,100,320,330,500,900,0},activity[7]={0,3,8,5,2,1,-3};
 int64_t m=0,a=0;int populations[2]={0};
 uint64_t h=hash_mix(2048+p->c)^(p->s<0?hash_mix(2064):0)^(p->e<0?0:hash_mix(2065+(p->e&7)));
 for(int q=0;q<128;q++){
  int v=p->b[q];need(!(q&0x88)||!v,"mailbox padding");if(!v||(q&0x88))continue;
  int k=abs(v),sign=v>0?1:-1;need(k<=6,"piece domain");populations[v<0]++;
  m+=sign*material[k];a+=sign*(activity[k]*center(q)+(k==1?6*((v>0?q/16:7-q/16)-1):0));
  h^=hash_mix((uint64_t)(q+(v+6)*128));
 }
 need(populations[0]<=16&&populations[1]<=16,"population domain");
 need(m==p->v&&a==p->a,"full independent model-input rebuild");
 need(llabs(m)<=14400&&llabs(a)<=1728,"admitted model-input bounds");need(h==p->h,"full independent position hash");
 int64_t raw=m+a+a*llabs(a)/128+p->s*10;
 need(llabs(raw)<=39466,"conservative int32 raw bound");scans++;
 return raw>20000?20000:raw< -20000?-20000:(int)raw;
}
static int order_reference(const za *p,Move m){
 const int material[7]={0,100,320,330,500,900,0};int from=FROM(m),to=TO(m),piece=p->b[from],a=abs(piece),v=abs(p->b[to]),prom=PROMO(m);
 if(a==1&&to==p->e&&!v)v=1;
 int score=2*(center(to)-center(from));if(v)score+=16*material[v]-material[a];
 if(prom)score+=12*(material[prom]-100);if(a==1)score+=4*(to/16-from/16)*(piece>0?1:-1);return score;
}
/* Original search calls these wrappers; only the two definition names change.
 * Both actual shipping bodies remain exact and are consumed by production M. */
static int S(const za *p){int expected=scalar(p),actual=shipping_S(p);need(actual==expected,"actual integer inference");leaf_calls++;return actual;}
static int R(const za *p,Move m){int expected=order_reference(p,m),actual=shipping_R(p,m);need(actual==expected,"actual five-feature ordering");order_calls++;return actual;}
static void check(const za *p){need(S(p)==scalar(p),"raw evaluator");}
static void empty(za *p){memset(p,0,sizeof *p);p->s=1;p->e=-1;p->h=O(p);}
static void load(za *p,const char *text){
 char cells[96],side,rights[8],ep[3];int half,full;static const char letters[]=" PNBRQK",flags[]="KQkq";
 need(sscanf(text,"%95s %c %7s %2s %d %d",cells,&side,rights,ep,&half,&full)==6,"fixture FEN fields");
 za t={0};t.s=side=='w'?1:-1;t.e=-1;t.zL=half;int rank=7,file=0;
 for(const char *c=cells;*c;c++)if(*c=='/'){rank--;file=0;}else if(isdigit((unsigned char)*c))file+=*c-'0';else{
  const char *k=strchr(letters,toupper((unsigned char)*c));need(k!=0,"fixture piece");H(&t,rank*16+file++,(int)(k-letters)*(isupper((unsigned char)*c)?1:-1));
 }
 for(const char *c=rights;*c&&*c!='-';c++){const char *k=strchr(flags,*c);need(k!=0,"fixture right");t.c|=1<<(k-flags);}
 if(ep[0]!='-')t.e=(ep[1]-'1')*16+ep[0]-'a';A(&t);t.h^=O(&t);t.r=t.h;*p=t;check(p);
}
static void children(const za *p,int recurse){
 za saved=*p;Move moves[MOVES];int n=gen(p,moves);check(p);
 for(int i=0;i<n;i++){
  R(p,moves[i]);za child;if(!make(p,moves[i],&child))continue;check(&child);legal_total++;
  need(memcmp(&saved,p,sizeof saved)==0,"parent state immutable");need(child.s==-p->s,"child side");
  need(child.r==(child.zL?((p->r<<1)|(p->r>>63))^child.h:child.h),"reversible TT context");
  int from=FROM(moves[i]),to=TO(moves[i]),color=p->s<0,cap=p->b[to]!=0;
  if(cap)captures|=1u<<color;if(abs(p->b[from])==1&&to==p->e&&!cap)eps|=1u<<color;
  if(abs(p->b[from])==6&&abs(to-from)==2)castles|=1u<<(color*2+(to<from));
  if(PROMO(moves[i])){promotions[color]|=1u<<PROMO(moves[i]);if(cap)promotion_captures[color]|=1u<<PROMO(moves[i]);}
  if(recurse)children(&child,0);
 }
}
static void scratch(const char *text,int requested,int expected){
 za p;load(&p,text);p.e=requested;za normal=p,poisoned=p;poisoned.v=INT_MAX;poisoned.a=INT_MIN;
 A(&normal);A(&poisoned);need(normal.e==expected&&poisoned.e==expected,"EP attack-only scratch independent of model state");
 need(poisoned.v==INT_MAX&&poisoned.a==INT_MIN&&!memcmp(normal.b,poisoned.b,128),"EP scratch does not escape or mutate inputs");
}
static void search_check(int black){
 za p;load(&p,black?"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
 y();memset(workers,0,sizeof workers);workers[0].zV=1;workers[0].zQ[0]=p.h;deadline=UINT64_MAX;atomic_store(&stopped,0);
 unsigned leaves=leaf_calls,orders=order_calls;Move best=0;int score=M(workers,&p,2,-MATE,MATE,0,0,&best);
 need(!atomic_load(&stopped)&&workers[0].z4>1&&leaf_calls>leaves&&order_calls>orders,"positive production search consumes both actual model bodies");
 Move moves[MOVES];int n=gen(&p,moves),found=0;for(int i=0;i<n;i++)if(moves[i]==best){za child;found=make(&p,best,&child);if(found)check(&child);}
 need(found&&abs(score)<=20000,"search legal normal result");printf("{\"kind\":\"search\",\"black\":%d,\"nodes\":%llu,\"score\":%d,\"best\":%u}\n",black,(unsigned long long)workers[0].z4,score,best);
}
int main(void){
 typedef struct{int8_t b[128];int s,c,e,k[2],zL;uint64_t h,r;} OldBoard;
 need(sizeof(OldBoard)==168&&sizeof(za)==176&&offsetof(za,v)==152&&offsetof(za,a)==156&&offsetof(za,h)==160&&offsetof(za,r)==168,"actual private model-state layout");
 const int16_t weights[19]={100,320,330,500,900,3,8,5,2,1,-3,6,10,1,16,-1,12,2,4};need(!memcmp(weights,tiny_weights,sizeof weights),"exact19 coefficients");
 for(int v=-6;v<=6;v++)for(int q=0;q<128;q++)if(!(q&0x88)){za p;empty(&p);H(&p,q,v);check(&p);H(&p,q,-v);check(&p);H(&p,q,0);check(&p);}
 for(int k=1;k<=6;k++){za p;empty(&p);for(int rank=0;rank<2;rank++)for(int f=0;f<8;f++){H(&p,rank*16+f,k);check(&p);H(&p,(rank+6)*16+f,-k);check(&p);}}
 /* Exact 64-bit oracle over the whole conservative activity interval and
  * material extrema. Synthetic accumulators test clamp/division, not state. */
 for(int a=-1728;a<=1728;a++)for(int side=-1;side<=1;side+=2)for(int sign=-1;sign<=1;sign+=2){
  za p={0};p.s=side;p.v=14400*sign;p.a=a;int64_t raw=(int64_t)p.v+a+(int64_t)a*llabs(a)/128+side*10;
  int expected=raw>20000?20000:raw< -20000?-20000:(int)raw;need(shipping_S(&p)==expected,"int64 range/division/clamp oracle");
 }
 za nonlinear[4];load(nonlinear,"7k/8/8/8/8/8/8/KN4N1 w - - 0 1");
 nonlinear[1]=nonlinear[0];H(nonlinear+1,1,0);H(nonlinear+1,34,2);
 nonlinear[2]=nonlinear[0];H(nonlinear+2,6,0);H(nonlinear+2,37,2);
 nonlinear[3]=nonlinear[1];H(nonlinear+3,6,0);H(nonlinear+3,37,2);
 for(int i=0;i<4;i++)check(nonlinear+i);
 need(S(nonlinear+3)-S(nonlinear+1)-S(nonlinear+2)+S(nonlinear)!=0,"actual nonadditive model interaction");
 za p;start(&p);children(&p,1);
 const char *cases[]={
 "4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1","4k3/8/8/3p4/4P3/8/8/4K3 b - - 0 1",
 "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",
 "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1","4k3/8/8/8/3Pp3/8/8/K3R3 b - d3 0 1",
 "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1","r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
 "1r5k/P7/8/8/8/8/8/7K w - - 0 1","7k/8/8/8/8/8/p7/1R5K b - - 0 1"};
 for(unsigned i=0;i<sizeof cases/sizeof *cases;i++){load(&p,cases[i]);children(&p,0);}
 scratch(cases[2],83,83);scratch(cases[3],35,35);scratch(cases[4],83,-1);scratch(cases[5],35,-1);
 need(captures==3&&eps==3&&castles==15&&promotions[0]==60&&promotions[1]==60&&promotion_captures[0]==60&&promotion_captures[1]==60,"both-color special-move coverage");
 table=calloc((size_t)1<<18,sizeof *table);need(table!=0,"fixture TT");search_check(0);search_check(1);free(table);
 printf("{\"kind\":\"summary\",\"old_board\":%zu,\"new_board\":%zu,\"scans\":%u,\"actual_leaf_calls\":%u,\"actual_order_calls\":%u,\"legal_children\":%u,\"pass\":true}\n",sizeof(OldBoard),sizeof(za),scans,leaf_calls,order_calls,legal_total);return 0;
}
