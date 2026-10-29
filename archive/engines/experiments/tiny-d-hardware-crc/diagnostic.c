#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "decoder.h"

#if CRC_ONLY
static cx_u32 software(cx_u32 h,unsigned char b){
    h^=b;
    for(unsigned k=0;k<8;k++)h=(h>>1)^(0x82f63b78u*(h&1));
    return h;
}
static unsigned tested;
static int compare(cx_u32 h,unsigned char b){
    tested++;
    if(cx_crc(h,b)==software(h,b))return 1;
    fprintf(stderr,"CRC mismatch seed=%08x byte=%02x case=%u\n",h,b,tested);
    return 0;
}
int main(void){
    const cx_u32 seeds[]={0,0xffffffffu,0x0101127eu,0x0810217eu,0x12345678u,0x80000000u};
    if(!compare(0,0))return 2;
    for(unsigned k=0;k<32;k++)if(!compare(1u<<k,0))return 2;
    for(unsigned k=0;k<8;k++)if(!compare(0,(unsigned char)(1u<<k)))return 2;
    for(unsigned s=0;s<sizeof seeds/sizeof *seeds;s++)
        for(unsigned b=0;b<256;b++)if(!compare(seeds[s],(unsigned char)b))return 2;
    cx_u32 state=0x6d2b79f5u;
    for(unsigned k=0;k<4096;k++){
        state^=state<<13;state^=state>>17;state^=state<<5;
        cx_u32 h=state;
        state^=state<<13;state^=state>>17;state^=state<<5;
        if(!compare(h,(unsigned char)state))return 2;
    }
    printf("{\"complete\":true,\"comparisons\":%u,\"zero\":1,\"seed_basis\":32,\"byte_basis\":8,\"all_byte_seed_pairs\":1536,\"random\":4096}\n",tested);
    return tested==5673?0:2;
}
#else
static unsigned char *read_file(const char *path,size_t *length){
    FILE *f=fopen(path,"rb");if(!f)return 0;
    if(fseek(f,0,SEEK_END)){fclose(f);return 0;}
    long n=ftell(f);if(n<=0||fseek(f,0,SEEK_SET)){fclose(f);return 0;}
    unsigned char *p=malloc((size_t)n);if(!p){fclose(f);return 0;}
    int ok=fread(p,1,(size_t)n,f)==(size_t)n;fclose(f);
    if(!ok){free(p);return 0;}*length=(size_t)n;return p;
}
static int save_file(const char *path,const unsigned char *p,size_t n){
    FILE *f=fopen(path,"wb");if(!f)return 0;
    int ok=fwrite(p,1,n,f)==n;return fclose(f)==0&&ok;
}
static void bcj(unsigned char *p,size_t n,int inverse){
    for(size_t i=0;i+4<n;){
        if((p[i]&254)==232){
            uint32_t value;memcpy(&value,p+i+1,4);
            value=inverse?value-(uint32_t)(i+5):value+(uint32_t)(i+5);
            memcpy(p+i+1,&value,4);i+=5;
        }else i++;
    }
}
int main(int argc,char **argv){
    if(argc!=5)return 2;
    size_t pn=0,n=0;unsigned char *packet=read_file(argv[1],&pn),*native=read_file(argv[2],&n);
    if(!packet||!native)return 2;
    unsigned char *allocation=malloc(n+32),*expected=malloc(n);
    unsigned char *table=mmap(0,33554432,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(!allocation||!expected||table==MAP_FAILED)return 2;
    memset(allocation,0xa5,n+32);memcpy(expected,native,n);bcj(expected,n,0);
    unsigned char *out=allocation+16;
    int status=context_decode(out,n,packet,packet+pn,table);
    int released=munmap(table,33554432)==0;
    int canaries=1;for(unsigned k=0;k<16;k++)canaries&=allocation[k]==0xa5&&out[n+k]==0xa5;
    int bcj_exact=!status&&!memcmp(out,expected,n);
    int saved_bcj=bcj_exact&&save_file(argv[3],out,n);
    if(!status)bcj(out,n,1);
    int native_exact=!status&&!memcmp(out,native,n);
    int saved_native=native_exact&&save_file(argv[4],out,n);
    printf("{\"complete\":%s,\"decode_status\":%d,\"bytes\":%zu,\"packet_bytes\":%zu,\"bcj_exact\":%s,\"native_exact\":%s,\"output_canaries\":%s,\"table_munmap\":%s}\n",
        !status&&released&&canaries&&bcj_exact&&native_exact&&saved_bcj&&saved_native?"true":"false",status,n,pn,
        bcj_exact?"true":"false",native_exact?"true":"false",canaries?"true":"false",released?"true":"false");
    free(packet);free(native);free(expected);free(allocation);
    return !status&&released&&canaries&&bcj_exact&&native_exact&&saved_bcj&&saved_native?0:2;
}
#endif
