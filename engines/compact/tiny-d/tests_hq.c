#include "hq.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

/* Independent coordinates: no production masks, reversal, or 0x88 rays. */
static uint64_t reference(uint64_t o,unsigned s,unsigned kind){
    uint64_t a=0;
    for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++){
        if((!dx&&!dy)||(kind==3&&(!dx||!dy))||(kind==4&&dx&&dy))continue;
        for(int x=(int)(s&7)+dx,y=(int)(s>>3)+dy;x>=0&&x<8&&y>=0&&y<8;x+=dx,y+=dy){
            uint64_t p=UINT64_C(1)<<(y*8+x);a|=p;if(o&p)break;
        }
    }
    return a;
}
static uint64_t checks;
static int check(uint64_t o,unsigned s,unsigned kind){
    unsigned q=(s>>3)*16+(s&7);
    uint64_t expected=reference(o,s,kind),actual=d_sliding(o,q,kind);
    checks++;
    if(expected==actual)return 1;
    fprintf(stderr,"slider mismatch s=%u kind=%u occ=%016" PRIx64 " expected=%016" PRIx64 " actual=%016" PRIx64 "\n",s,kind,o,expected,actual);
    return 0;
}
static uint64_t random64(uint64_t *seed){
    uint64_t x=*seed;x^=x<<13;x^=x>>7;x^=x<<17;return *seed=x;
}
int main(void){
    uint64_t seed=UINT64_C(0x14cd9e5f238a76b1),subsets=0,boards=0;
    for(unsigned s=0;s<64;s++){
        uint64_t source=UINT64_C(1)<<s;
        for(unsigned kind=3;kind<=4;kind++){
            uint64_t ray=reference(0,s,kind),o=0;
            do{
                /* Every combination of every on-ray square, including edges;
                 * also prove source occupancy and all off-ray bits irrelevant. */
                if(!check(o,s,kind)||!check(o|source,s,kind)||!check(o|~ray,s,kind))return 1;
                subsets++;o=(o-ray)&ray;
            }while(o);
        }
        for(unsigned i=0;i<4096;i++){
            uint64_t o=random64(&seed);
            for(unsigned kind=3;kind<=5;kind++)if(!check(o,s,kind)||!check(o&~source,s,kind))return 1;
        }
    }
    for(unsigned i=0;i<8192;i++){
        int8_t b[128];memset(b,99,sizeof b);uint64_t expected=random64(&seed);
        for(unsigned s=0;s<64;s++)b[(s>>3)*16+(s&7)]=(expected>>s)&1?(s&1?-6:3):0;
        if(d_occupancy(b)!=expected){fputs("occupancy conversion mismatch\n",stderr);return 1;}
        boards++;
    }
    printf("{\"slider_checks\":%" PRIu64 ",\"exhaustive_ray_subsets\":%" PRIu64 ",\"mailbox_boards\":%" PRIu64 ",\"passed\":true}\n",checks,subsets,boards);
    return 0;
}
