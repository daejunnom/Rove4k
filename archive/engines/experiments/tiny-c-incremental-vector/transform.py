"""ONE pinned private Board feature-state change; no normal source edits."""
import hashlib
BASE_SHA='207b07cc623e5408e868591770782676ccba189af50533f23533ac76ae8cb44c'
CANDIDATE_SHA='8fd32643582b3b485cdfa077fb20ada4af67c8cc0f867206f4c4f425312b9caf'
PAIRS=[(b'typedef unsigned Move;typedef struct{int8_t b[128];int s,c,e,k[2],zL;uint64_t h,r;}za;', b'typedef unsigned Move;typedef struct{int8_t b[128];int16_t x[16];int s,c,e,k[2],zL;uint64_t h,r;}za;'), (b'static uint64_t H(int v,int q){return mix((uint64_t)(q+(v+6)*128));}', b'static uint64_t H(za*p,int v,int q,int n){int k=abs(v),o=8*(v<0),t=value(v,q);p->x[o+k-1]+=n;p->x[o+6]+=n*((v>0?t:-t)-qm[k-1]);return mix((uint64_t)(q+(v+6)*128));}'), (b'static void K(za*p,int q,int v){int a=p->b[q];if(a){p->h^=H(a,q);}p->b[q]=(int8_t)v;if(v){p->h^=H(v,q);if(abs(v)==6)p->k[v<0]=q;}}', b'static void K(za*p,int q,int v){int a=p->b[q];if(a){p->h^=H(p,a,q,-1);}p->b[q]=(int8_t)v;if(v){p->h^=H(p,v,q,1);if(abs(v)==6)p->k[v<0]=q;}}'), (b'static int U(const za*p){int16_t x[16]={0};for(int q=0;q<128;q++)if(!(q&0x88)){int v=p->b[q];if(v){int k=abs(v),o=8*(v<0),t=value(v,q);x[o+k-1]++;x[o+6]+=(v>0?t:-t)-qm[k-1];}}__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)x),_mm256_loadu_si256((const __m256i*)qm));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}', b'static int U(const za*p){__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)p->x),_mm256_loadu_si256((const __m256i*)qm));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}')]
def transform(source):
    if len(source)!=10831 or hashlib.sha256(source).hexdigest()!=BASE_SHA:
        raise ValueError('exact current material-vector shipping source required')
    result=source;old_rest=source;new_rest=source
    for old,new in PAIRS:
        if result.count(old)!=1:raise ValueError('fixed old span is not unique')
        result=result.replace(old,new,1)
    inverse=result;new_rest=result
    for index,(old,new)in enumerate(PAIRS):
        if inverse.count(new)!=1:raise ValueError('fixed new span is not unique')
        inverse=inverse.replace(new,old,1)
        marker=('$SPAN'+str(index)).encode()
        old_rest=old_rest.replace(old,marker,1);new_rest=new_rest.replace(new,marker,1)
    if inverse!=source or old_rest!=new_rest:raise ValueError('inverse/complement changed')
    if len(result)!=10803 or hashlib.sha256(result).hexdigest()!=CANDIDATE_SHA:
        raise ValueError('fixed candidate differs')
    return result
