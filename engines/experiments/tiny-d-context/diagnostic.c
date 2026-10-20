#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include "decoder.h"

/* Test-only libc caller: right-aligned buffers end immediately at PROT_NONE.
 * The decoder header is included unchanged, with no instrumentation hooks. */
typedef struct {
    unsigned char *mapping,*data;
    size_t total,pages,prefix,size;
} Guard;

static int reserve(Guard *g,size_t size,unsigned char fill){
    size_t page=(size_t)sysconf(_SC_PAGESIZE);
    if(!page || page!=(size_t)4096 || !size || size>33554432)return 1;
    g->size=size;g->pages=(size+page-1)/page*page;
    g->total=g->pages+page*2;g->prefix=g->pages-size;
    g->mapping=mmap(0,g->total,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(g->mapping==MAP_FAILED){g->mapping=0;return 1;}
    if(mprotect(g->mapping+page,g->pages,PROT_READ|PROT_WRITE))return 1;
    g->data=g->mapping+page+g->prefix;
    if(fill)memset(g->mapping+page,fill,g->pages);
    return 0;
}

static int size_of_file(const char *path,size_t *size){
    struct stat st;
    if(stat(path,&st) || st.st_size<=0 || st.st_size>1048576)return 1;
    *size=(size_t)st.st_size;
    return 0;
}

static int load_file(const char *path,unsigned char *data,size_t size){
    int fd=open(path,O_RDONLY);
    if(fd<0)return 1;
    size_t at=0;
    while(at<size){
        ssize_t got=read(fd,data+at,size-at);
        if(got<=0){close(fd);return 1;}
        at+=(size_t)got;
    }
    unsigned char extra;
    int bad=read(fd,&extra,1)!=0;
    if(close(fd))bad=1;
    return bad;
}

int main(int argc,char **argv){
    Guard input={0},output={0},table={0};
    unsigned char *expected=0;
    size_t input_size=0,output_size=0;
    int status=1,decoded=-1,equal=0,canary=0,unmap_errors=0,guarded=0,input_ro=0,table_zero=0;
    const char *phase="arguments";
    if(argc!=3)goto done;
    phase="input-size";
    if(size_of_file(argv[1],&input_size) || size_of_file(argv[2],&output_size))goto done;
    phase="guard-mappings";
    if(reserve(&input,input_size,0x5a) || reserve(&output,output_size,0xa5) || reserve(&table,33554432,0))goto done;
    guarded=table_zero=1;
    phase="load-input";
    if(load_file(argv[1],input.data,input_size))goto done;
    if(mprotect(input.mapping+4096,input.pages,PROT_READ))goto done;
    input_ro=1;
    expected=malloc(output_size);
    if(!expected || load_file(argv[2],expected,output_size))goto done;
    phase="decode";
    decoded=context_decode(output.data,output_size,input.data,input.data+input_size,table.data);
    equal=!memcmp(expected,output.data,output_size);
    canary=1;
    for(size_t i=0;i<output.prefix;i++)if(output.mapping[4096+i]!=0xa5)canary=0;
    if(decoded || !equal || !canary)goto done;
    status=0;phase="complete";
done:
    free(expected);
    if(table.mapping && munmap(table.mapping,table.total))unmap_errors++;
    if(output.mapping && munmap(output.mapping,output.total))unmap_errors++;
    if(input.mapping && munmap(input.mapping,input.total))unmap_errors++;
    if(unmap_errors)status=1;
    printf("{\"complete\":%s,\"phase\":\"%s\",\"decode_result\":%d,"
           "\"input_bytes\":%zu,\"output_bytes\":%zu,\"byte_equal\":%s,"
           "\"output_prefix_canary\":%s,\"guarded_input_output_table\":%s,"
           "\"input_read_only\":%s,\"table_zero_anonymous\":%s,\"unmap_errors\":%d}\n",
           status?"false":"true",phase,decoded,input_size,output_size,equal?"true":"false",canary?"true":"false",
           guarded?"true":"false",input_ro?"true":"false",table_zero?"true":"false",unmap_errors);
    return status;
}
