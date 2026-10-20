"""Fixed ordinary signed-net8lane closing stage after incremental.

x0 is zero padding; x1..6 are white-black PNBRQK counts; x7 is signed
positional residual. Material + residual equals the original full HCE.
The natural piece index preserves value(0,q)=0 and the zero king material
lane retains its PST in residual. Counts <=16 and residual <=2016 fit i16.
U uses actual128-bit madd/hadd under unchanged -mavx2 compiler flags;
SSE2/SSSE3 intrinsic requirements are distinct from256-bit AVX2 leaf use.
Whole-source pins, five literal regions, inverse and complement close the
exact selected source. Canonical/gather DEV and all earlier guards stay.
No experiment, generated output, report or model parameter input is read.
"""
import hashlib
BASE_SHA='8fd32643582b3b485cdfa077fb20ada4af67c8cc0f867206f4c4f425312b9caf'
CANDIDATE_SHA='58e71a9c05cb48e4d1a8de83cd833981f64165344f53c41d0c39542fdfb1ae64'
PAIRS=[(b'int16_t x[16];', b'int16_t x[8];'), (b'static const int16_t qm[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};', b'static const int16_t qm[8]={0,100,320,330,500,900,0,1};'), (b'int m=-qm[a+7]+', b'int m=qm[a]+'), (b'static uint64_t H(za*p,int v,int q,int n){int k=abs(v),o=8*(v<0),t=value(v,q);p->x[o+k-1]+=n;p->x[o+6]+=n*((v>0?t:-t)-qm[k-1]);return mix((uint64_t)(q+(v+6)*128));}', b'static uint64_t H(za*p,int v,int q,int n){int k=abs(v),s=v>0?n:-n;p->x[k]+=s;p->x[7]+=n*value(v,q)-s*qm[k];return mix((uint64_t)(q+(v+6)*128));}'), (b'static int U(const za*p){__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)p->x),_mm256_loadu_si256((const __m256i*)qm));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}', b'static int U(const za*p){__m128i z=_mm_madd_epi16(_mm_loadu_si128((const __m128i*)p->x),_mm_loadu_si128((const __m128i*)qm));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}')]

def transform_source(source):
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
    return result, {'fixed_regions':5,'inverse_equal':True,'protected_complement_equal':True,'feature_lanes_i16':8,'count_abs_upper':16,'signed_residual_abs_upper':2016,'padding_zero_lane':0,'king_material_zero_lane':6,'actual_SIMD_width_bits':128,'intrinsic_minimum_ISA':'SSE2 madd + SSSE3 hadd','fixed_compiler_flag':'-mavx2','AVX2_256_leaf_claim':False,'canonical_DEV_and_prior_stages_unchanged':True}
