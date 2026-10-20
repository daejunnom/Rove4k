/* Positive exact-byte diagnostic only. No engine, fault or negative input. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/mman.h>
#include "decoder.h"

static unsigned char *read_bytes(const char *name, size_t *size) {
    FILE *f=fopen(name,"rb");
    if(!f || fseek(f,0,SEEK_END))exit(20);
    long n=ftell(f);
    if(n<0 || n>1048576 || fseek(f,0,SEEK_SET))exit(21);
    unsigned char *p=malloc((size_t)n+1);
    if(!p || fread(p,1,(size_t)n,f)!=(size_t)n || fclose(f))exit(22);
    *size=(size_t)n;return p;
}
static void write_bytes(const char *name,const unsigned char *p,size_t n) {
    FILE *f=fopen(name,"wb");
    if(!f || fwrite(p,1,n,f)!=n || fclose(f))exit(23);
}
static void bcj(unsigned char *p,size_t n,int inverse) {
    for(size_t i=0;i+4<n;) {
        if((p[i]&254)==232) {
            uint32_t v;memcpy(&v,p+i+1,4);
            v=inverse?v-(uint32_t)(i+5):v+(uint32_t)(i+5);
            memcpy(p+i+1,&v,4);i+=5;
        } else i++;
    }
}
int main(int argc,char **argv) {
    if(argc!=5)return 24;
    size_t n,pn;
    unsigned char *native=read_bytes(argv[1],&n),*payload=read_bytes(argv[2],&pn);
    if(n!=IMAGE_SIZE || pn<25)return 25;
    unsigned char *buffer=malloc(n+64),*expected=malloc(n);
    if(!buffer || !expected)return 26;
    memset(buffer,0xa5,n+64);memcpy(expected,native,n);bcj(expected,n,0);
    unsigned char *out=buffer+32;
    void *table=mmap(0,33554432,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(table==MAP_FAILED)return 27;
    int rc=context_decode(out,n,payload,payload+pn,table);
    if(rc || memcmp(out,expected,n))return 28;
    for(unsigned i=0;i<32;i++)if(buffer[i]!=0xa5 || out[n+i]!=0xa5)return 29;
    write_bytes(argv[3],out,n);
    bcj(out,n,1);
    if(memcmp(out,native,n))return 30;
    write_bytes(argv[4],out,n);
    if(munmap(table,33554432))return 31;
    printf("{\"complete\":true,\"decoded_bytes\":%zu,\"payload_bytes\":%zu,\"exact_BCJ\":true,\"exact_native\":true,\"canaries\":true,\"context_unmapped\":true,\"negative_cases\":0}\n",n,pn);
    free(buffer);free(expected);free(native);free(payload);return 0;
}