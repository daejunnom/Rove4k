"""Fixed ordinary closing stage: share C material with its SIMD weights."""
import hashlib
import re

BASE_BYTES = 10886
BASE_SHA = 'd6265b2cabf0dfbe96744acc9cbfcccfe29c0a292901b326ee2f1f061b93aeca'
CANDIDATE_BYTES = 10831
CANDIDATE_SHA = '207b07cc623e5408e868591770782676ccba189af50533f23533ac76ae8cb44c'
OLD_VALUE = b'int value(int v,int q){static const int material[7]={0,100,320,330,500,900,0};int a=abs(v),d=q>>4,f=q&7,i=v>0?d:7-d;int j=7-abs(2*f-7)-abs(2*d-7);int m=material[a]+i*(a==1?7:a==4?2:0)+j*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);return v>0?m:-m;}'
NEW_VALUE = b'static const int16_t qm[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};int value(int v,int q){int a=abs(v),d=q>>4,f=q&7,i=v>0?d:7-d;int j=7-abs(2*f-7)-abs(2*d-7);int m=-qm[a+7]+i*(a==1?7:a==4?2:0)+j*(a==2?9:a==3?5:a==6?-3:(a==1||a==5)*2);return v>0?m:-m;}'
OLD_U = b'static int U(const za*p){static const int16_t w[16]={100,320,330,500,900,0,1,0,-100,-320,-330,-500,-900,0,-1,0};int16_t x[16]={0};for(int q=0;q<128;q++)if(!(q&0x88)){int v=p->b[q];if(v){int k=abs(v),o=8*(v<0),t=value(v,q);x[o+k-1]++;x[o+6]+=(v>0?t:-t)-w[k-1];}}__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)x),_mm256_loadu_si256((const __m256i*)w));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}'
NEW_U = b'static int U(const za*p){int16_t x[16]={0};for(int q=0;q<128;q++)if(!(q&0x88)){int v=p->b[q];if(v){int k=abs(v),o=8*(v<0),t=value(v,q);x[o+k-1]++;x[o+6]+=(v>0?t:-t)-qm[k-1];}}__m256i y=_mm256_madd_epi16(_mm256_loadu_si256((const __m256i*)x),_mm256_loadu_si256((const __m256i*)qm));__m128i z=_mm_add_epi32(_mm256_castsi256_si128(y),_mm256_extracti128_si256(y,1));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform_source(source):
    if len(source) != BASE_BYTES or sha(source) != BASE_SHA:
        raise ValueError('exact post-input-profile C shipping source required')
    if re.search(rb'\bqm\b', source):
        raise ValueError('qm is not source-fresh')
    pairs = ((OLD_VALUE, NEW_VALUE), (OLD_U, NEW_U))
    result = source
    for old, new in pairs:
        if result.count(old) != 1:
            raise ValueError('fixed old span is not unique')
        result = result.replace(old, new, 1)
    inverse = result
    old_complement, new_complement = source, result
    for index, (old, new) in enumerate(pairs):
        if inverse.count(new) != 1:
            raise ValueError('fixed new span is not unique')
        inverse = inverse.replace(new, old, 1)
        marker = ('$SPAN' + str(index)).encode()
        old_complement = old_complement.replace(old, marker, 1)
        new_complement = new_complement.replace(new, marker, 1)
    if inverse != source or old_complement != new_complement:
        raise ValueError('inverse or protected complement changed')
    if len(result) != CANDIDATE_BYTES or sha(result) != CANDIDATE_SHA:
        raise ValueError('fixed candidate identity differs')
    if len(re.findall(rb'\bqm\b', result)) != 4 or len(re.findall(rb'\bvalue\b', result)) != 4:
        raise ValueError('fixed name/consumer count differs')
    return result, {'inverse_equal': True, 'protected_complement_equal': True,
                    'source_bytes_delta': -55, 'qm_tokens_before': 0,
                    'qm_tokens_after': 4, 'value_definition_and_calls': 4,
                    'canonical_DEV_and_earlier_stages_unchanged': True}
