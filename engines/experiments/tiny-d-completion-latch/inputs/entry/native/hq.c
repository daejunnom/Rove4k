#include "hq.h"
#ifndef D_HQ
#define D_HQ 1
#endif

uint64_t d_occupancy(const int8_t b[128]){
    uint64_t o=0;
    for(unsigned q=0;q<128;q++)if(!(q&0x88)&&b[q])o|=UINT64_C(1)<<((q>>4)*8+(q&7));
    return o;
}

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
    unsigned r=q>>4,f=q&7;
    uint64_t p=UINT64_C(1)<<(r*8+f),a=0;
    if(kind!=3)a=line(o,p,UINT64_C(255)<<(r*8))|line(o,p,UINT64_C(0x0101010101010101)<<f);
    if(kind!=4)a|=line(o,p,shift(UINT64_C(0x8040201008040201),(int)r-(int)f))|
                  line(o,p,shift(UINT64_C(0x0102040810204080),(int)r+(int)f-7));
    return a;
}
#else
uint64_t d_sliding(uint64_t o,unsigned q,unsigned kind){
    static const int rays[8]={1,-1,16,-16,17,15,-15,-17};
    uint64_t a=0;
    for(int i=kind==3?4:0;i<(kind==4?4:8);i++)for(int t=(int)q+rays[i];!(t&0x88);t+=rays[i]){
        uint64_t p=UINT64_C(1)<<((t>>4)*8+(t&7));a|=p;if(o&p)break;
    }
    return a;
}
#endif
