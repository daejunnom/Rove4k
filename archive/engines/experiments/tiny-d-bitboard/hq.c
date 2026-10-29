#include "hq.h"
#ifndef D_HQ
#define D_HQ 1
#endif
#if D_HQ
static uint64_t reverse(uint64_t x){
    x=((x>>1)&UINT64_C(0x5555555555555555))|((x&UINT64_C(0x5555555555555555))<<1);
    x=((x>>2)&UINT64_C(0x3333333333333333))|((x&UINT64_C(0x3333333333333333))<<2);
    x=((x>>4)&UINT64_C(0x0f0f0f0f0f0f0f0f))|((x&UINT64_C(0x0f0f0f0f0f0f0f0f))<<4);
    return __builtin_bswap64(x);
}
static uint64_t line(uint64_t o,uint64_t p,uint64_t mask){
    o&=mask;
    return ((o-p*2)^reverse(reverse(o)-reverse(p)*2))&mask;
}
static uint64_t shift(uint64_t x,int ranks){return ranks<0?x>>(-ranks*8):x<<(ranks*8);}
uint64_t d_sliding(uint64_t o,unsigned q,unsigned kind){
    unsigned r=q>>3,f=q&7;uint64_t p=UINT64_C(1)<<q,a=0;
    if(kind!=2)a=line(o,p,UINT64_C(255)<<(r*8))|line(o,p,UINT64_C(0x0101010101010101)<<f);
    if(kind!=3)a|=line(o,p,shift(UINT64_C(0x8040201008040201),(int)r-(int)f))|
                  line(o,p,shift(UINT64_C(0x0102040810204080),(int)r+(int)f-7));
    return a;
}
#else
uint64_t d_sliding(uint64_t o,unsigned q,unsigned kind){
    static const int df[8]={1,-1,0,0,1,-1,1,-1},dr[8]={0,0,1,-1,1,1,-1,-1};
    uint64_t a=0;
    for(int i=kind==2?4:0;i<(kind==3?4:8);i++){
        int f=(int)(q&7)+df[i],r=(int)(q>>3)+dr[i];
        for(;f>=0&&f<8&&r>=0&&r<8;f+=df[i],r+=dr[i]){
            uint64_t p=UINT64_C(1)<<(r*8+f);a|=p;if(o&p)break;
        }
    }
    return a;
}
#endif
