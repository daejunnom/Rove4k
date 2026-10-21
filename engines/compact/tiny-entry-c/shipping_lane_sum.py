"""Pure late C128-bit madd reduction spelling; canonical/gather DEV bypass it.

The same initialized eight signed16 features, coefficients and16-byte loads
feed the unchanged madd. Four signed32 result lanes sum within70483968,
including every partial sum, so the scalar association is defined. This fixed
GCC13 GNU-vector value cast introduces no pointer alias or target ISA change.
No external evidence, compiler, parser, codec or runtime input is read.
"""
import hashlib

BEFORE=(9882,'11b0c4ee8703d0feac9338ddf8b53e7225e92d644a57c3351be22585f28e538a')
AFTER=(9848,'a661656a482be3ee8383443925c7c36114ce802e9d06ffed59f5479f7ccd37b9')
OFFSET=3880
OLD=b'static int U(const za*p){__m128i z=_mm_madd_epi16(_mm_loadu_si128((const __m128i*)p->x),_mm_loadu_si128((const __m128i*)qm));z=_mm_hadd_epi32(z,z);return _mm_cvtsi128_si32(_mm_hadd_epi32(z,z));}'
NEW=b'static int U(const za*p){__v4si z=(__v4si)_mm_madd_epi16(_mm_loadu_si128((const __m128i*)p->x),_mm_loadu_si128((const __m128i*)qm));return z[0]+z[1]+z[2]+z[3];}'
GAPS=((0, 0, 3880, 'e6e1cdbeb031aacf7f379f8a3576af553eaa93a141136b0e136cd258205117be'), (4074, 4040, 5808, 'f469b07034e87984d0bdfd601e05aea1d52070cf304a277c650d19eada8ab8cd'))

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def _need(ok,message):
    if not ok:raise ValueError(message)

def transform_source(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed after-capture C source required')
    _need(source[OFFSET:OFFSET+len(OLD)]==OLD and source.count(OLD)==1,'sole C signed8 evaluator differs')
    candidate=source[:OFFSET]+NEW+source[OFFSET+len(OLD):]
    _need(_pin(candidate)==AFTER,'fixed C scalar-lane reduction differs')
    _need(candidate[:OFFSET]+OLD+candidate[OFFSET+len(NEW):]==source,'C lane-sum full inverse differs')
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        _need(old==new and hashlib.sha256(old).hexdigest()==digest,'C lane-sum protected gap differs')
    return candidate,{'stage':'C shipping after capture metadata','input_bytes':BEFORE[0],
        'input_sha256':BEFORE[1],'output_bytes':AFTER[0],'output_sha256':AFTER[1],
        'literal_regions':1,'protected_gaps':2,'full_inverse':True,'all_gaps_equal':True,
        'raw_source_delta':-34,'feature_lanes_i16':8,'actual_madd_width_bits':128,
        'weights_unchanged':True,'initialized_i16_partial_sum_abs_bound':70483968,
        'vector_value_cast':'fixed GCC13 __m128i16B to signed-int __v4si16B',
        'canonical_DEV_Board_learners_search_threads_changed':False,
        'compiler_mavx2_unchanged':True,'native_identity_changed':True,'external_reads':0}
