#ifndef ROVE_CONTEXT_DECODER_H
#define ROVE_CONTEXT_DECODER_H

/* Independent integer decoder. H24/base10 and a u32 length are format ABI.
 * The caller supplies a zeroed 32 MiB table and four real zero tail bytes.
 * History and the current-byte prefix never read or write outside out[0,size).
 */
typedef unsigned int cx_u32;
typedef unsigned long long cx_u64;
_Static_assert(sizeof(cx_u32)==4 && sizeof(cx_u64)==8, "context integer widths");

typedef struct {
    const unsigned char *p,*end;
    unsigned bit;
} cx_input;

static cx_u32 cx_le32(const unsigned char *p){
    return (cx_u32)p[0]|(cx_u32)p[1]<<8|(cx_u32)p[2]<<16|(cx_u32)p[3]<<24;
}

static cx_u32 cx_crc(cx_u32 h,unsigned char b){
    h^=b;
    for(unsigned k=0;k<8;k++)h=(h>>1)^(0x82f63b78u*(h&1));
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
    cx_u32 seeds[21],slots[21],n=0,w,scan,weight=0;
    unsigned char weights[21];
    if(end<begin || (unsigned long)(end-begin)<12 || size>0x1ffffffful)return 1;
    for(unsigned k=1;k<=4;k++)if(end[-(int)k])return 1;
    cx_u32 bits=cx_le32(begin);
    if(bits!=(cx_u32)size*8+1)return 2;
    w=scan=cx_le32(begin+4);
    for(;;){
        cx_u32 one=scan>>31;
        scan<<=1;
        if(!scan)break;
        if(!one && ++n>21)return 3;
    }
    if((unsigned long)(end-begin)<12+n)return 3;
    for(cx_u32 j=0;j<n;j++){
        while(w>>31){w<<=1;if(++weight>9)return 3;}
        w<<=1;
        weights[j]=(unsigned char)weight;
        seeds[j]=(w&0xffffff00u)|begin[8+j];
    }
    cx_input in={begin+8+n,end,0};
    cx_u32 value=0,range=0x80000000u,prefix=0;
    cx_u64 history=0;
    unsigned long written=0;
    for(unsigned k=0;k<31;k++)if(cx_append(&in,&value))return 4;
    for(cx_u32 left=bits;left;left--){
        cx_u32 p0=10,p1=10;
        for(cx_u32 j=0;j<n;j++){
            cx_u32 hash=cx_crc(seeds[j],(unsigned char)prefix);
            unsigned char mask=(unsigned char)seeds[j];
            cx_u64 past=history;
            while(mask){
                if(mask&128)hash=cx_crc(hash,(unsigned char)past);
                mask=(unsigned char)(mask<<1);past>>=8;
            }
            cx_u32 at=(hash>>8)*2,c0=table[at],c1=table[at+1];
            unsigned shift=weights[j]+((!c0 || !c1)?2:0);
            slots[j]=at;p0+=c0<<shift;p1+=c1<<shift;
        }
        /* With <=21 byte-counter models and weights<=9, these sums fit u32
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
        for(cx_u32 j=0;j<n;j++){
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
