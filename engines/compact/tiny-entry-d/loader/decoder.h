#ifndef ROVE_CONTEXT_DECODER_H
#define ROVE_CONTEXT_DECODER_H

/* Fixed21 replay ABI: IMAGE_SIZE owns u32 coded count, MODEL_WMASK is a
 * source-pinned form literal. Stream is mask21, body, and real zero4.
 * The caller supplies a zeroed 32 MiB table and four real zero tail bytes.
 * History and the current-byte prefix never read or write outside out[0,size).
 */
#ifndef MODEL_WMASK
#error "fixed profile MODEL_WMASK required"
#endif
typedef unsigned int cx_u32;
typedef unsigned long long cx_u64;
_Static_assert(sizeof(cx_u32)==4 && sizeof(cx_u64)==8, "context integer widths");
_Static_assert((cx_u32)MODEL_WMASK==0x0101127eu ||
               (cx_u32)MODEL_WMASK==0x0810217eu, "exact fixed profile");

typedef struct {
    const unsigned char *p,*end;
    unsigned bit;
} cx_input;

static cx_u32 cx_crc(cx_u32 h,unsigned char b){
    __asm__("crc32b %1,%0":"+r"(h):"qm"(b));
    return h;
}

static int cx_append(cx_input *in,cx_u32 *value){
    if(in->p==in->end)return 1;
    *value=(*value<<1)|((*in->p>>in->bit)&1u);
    if(++in->bit==8)in->bit=0,in->p++;
    return 0;
}

static int context_decode(unsigned char *out,unsigned long size,
    const unsigned char *begin,const unsigned char *end,unsigned char *table){
    cx_u32 slots[21];
    if(end<begin || (unsigned long)(end-begin)<25 || size>0x1ffffffful)return 1;
    for(unsigned k=1;k<=4;k++)if(end[-(int)k])return 1;
    cx_u32 bits=(cx_u32)size*8+1;
    cx_input in={begin+21,end,0};
    cx_u32 value=0,range=0x80000000u,prefix=0;
    cx_u64 history=0;
    unsigned long written=0;
    for(unsigned k=0;k<31;k++)if(cx_append(&in,&value))return 4;
    for(cx_u32 left=bits;left;left--){
        cx_u32 p0=10,p1=10,w=(cx_u32)MODEL_WMASK,weight=0;
        for(cx_u32 j=0;j<21;j++){
            while(w>>31){w<<=1;weight++;}
            w<<=1;
            cx_u32 seed=(w&0xffffff00u)|begin[j];
            cx_u32 hash=cx_crc(seed,(unsigned char)prefix);
            unsigned char mask=(unsigned char)seed;
            cx_u64 past=history;
            while(mask){
                if(mask&128)hash=cx_crc(hash,(unsigned char)past);
                mask=(unsigned char)(mask<<1);past>>=8;
            }
            cx_u32 at=(hash>>8)*2,c0=table[at],c1=table[at+1];
            unsigned shift=weight+((!c0 || !c1)?2:0);
            slots[j]=at;p0+=c0<<shift;p1+=c1<<shift;
        }
        /* With exactly21 fixed models and weights<=4, these sums fit u32
         * and the product fits u64. Base10 keeps both subranges nonzero. */
        cx_u32 cut=(cx_u32)((cx_u64)range*p1/(p0+p1));
        unsigned bit=value<cut;
        if(bit)range=cut;
        else value-=cut,range-=cut;
        while(!(range&0x80000000u)){
            range<<=1;
            if(cx_append(&in,&value))return 4;
        }
        /* All probabilities were read before any slot is updated. Aliased
         * slots still receive one update per model, including byte wrap. */
        for(cx_u32 j=0;j<21;j++){
            cx_u32 at=slots[j];
            table[at+bit]++;
            if(table[at+(bit^1)]>1)table[at+(bit^1)]>>=1;
        }
        if(!prefix){if(!bit)return 5;prefix=1;continue;}
        prefix=prefix*2+bit;
        if(prefix>=256){
            if(written==size)return 6;
            unsigned char byte=(unsigned char)prefix;
            out[written++]=byte;history=(history<<8)|byte;prefix=1;
        }
    }
    return written==size && prefix==1?0:6;
}
#endif
