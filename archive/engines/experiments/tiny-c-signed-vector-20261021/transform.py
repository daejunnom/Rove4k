"""ONE C signed-net8lane exact HCE representation; no normal edits."""
import hashlib
BASE_SHA='8fd32643582b3b485cdfa077fb20ada4af67c8cc0f867206f4c4f425312b9caf'
CANDIDATE_SHA='58e71a9c05cb48e4d1a8de83cd833981f64165344f53c41d0c39542fdfb1ae64'
PAIRS=[(b'int16_t x[16];', b'int16_t x[8];'), (b'static const int16_t qm[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};', b'static const int16_t qm[8]={0,100,320,330,500,900,0,1};'), (b'int m=-qm[a+7]+', b'int m=qm[a]+'), (b'static uint64_t H(za*p,int v,int q,int n){int k=abs(v),o=8*(v<0),t=value(v,q);p->x[o+k-1]+=n;p->x[o+6]+=n*((v>0?t:-t)-qm[k-1]);return mix((uint64_t)(q+(v+6)*128));}', b'static uint64_t H(za*p,int v,int q,int n){int k=abs(v),s=v>0?n:-n;p->x[k]+=s;p->x[7]+=n*value(v,q)-s*qm[k];return mix((uint64_t)(q+(v+6)*128));}'), (b'static int U(const za*p){__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)p->x),_mm256_loadu_si256((const __m256i*)qm));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}', b'static int U(const za*p){__m128i z=_mm_madd_epi16(_mm_loadu_si128((const __m128i*)p->x),_mm_loadu_si128((const __m128i*)qm));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}')]

def transform(source):
    if len(source)!=10803 or hashlib.sha256(source).hexdigest()!=BASE_SHA:
        raise ValueError('exact current C private16lane source required')
    result=source;old_rest=source
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
    if len(result)!=10656 or hashlib.sha256(result).hexdigest()!=CANDIDATE_SHA:
        raise ValueError('fixed candidate differs')
    return result
