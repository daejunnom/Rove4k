"""Pure E late center construction sharing in the actual valid0x88 caller domain.

The original readable model/DEV admission stays before this stage. No I/O,
research artifact, model coefficient change or executable is consumed here.
"""
import hashlib

INPUT_BYTES=10200
INPUT_SHA='6d336854f38c3a1aaf2b3facb7487aa3ece687f5280a5e9315eb08b2425bf329'
OUTPUT_BYTES=10190
OUTPUT_SHA='34cc868b06252cb25a58be54d9e8fecb26cd6705d159533363ab57aa96b70bcd'
AT=1124
OLD=b'static int Q(int q){int f=q&7,r=q>>4;return(f<4?f:7-f)+(r<4?r:7-r);}'
NEW=b'static int Q(int q){return 7-(abs(q%8*2-7)+abs(q/8-7))/2;}'
GAPS=((0, 0, 1124, 'c48477b243af3af9f1af081e65aca69385fcbd4e66c4a4a995ab577a12c574f7'), (1192, 1182, 9008, '3f6c275104a658ef9c997052ee02204edd4fdd64783ed05d7ea3bb47cff605d2'))
COMPLEMENT_BYTES=10132
COMPLEMENT_SHA='576a1bef4acf3a1dbcfef367dec6777ba2309d22614f71272d0a8cc3af04eaf5'
METADATA={'family': 'E', 'stage': 'late-shipping-centered-center-feature', 'input_bytes': 10200, 'input_sha256': '6d336854f38c3a1aaf2b3facb7487aa3ece687f5280a5e9315eb08b2425bf329', 'output_bytes': 10190, 'output_sha256': '34cc868b06252cb25a58be54d9e8fecb26cd6705d159533363ab57aa96b70bcd', 'raw_delta': -10, 'owned_regions': 1, 'protected_gaps': 2, 'full_inverse': True, 'all_gaps_equal': True, 'protected_complement_bytes': 10132, 'protected_complement_sha256': '576a1bef4acf3a1dbcfef367dec6777ba2309d22614f71272d0a8cc3af04eaf5', 'actual_call_contract': 'Q consumes valid0x88 squares through H/d piece-activity updates and R generated FROM/TO center delta', 'square_domain': 'q=16*rank+file, file/rank0..7; q%8=file, q/8=2*rank', 'abs_argument_bounds': [-7, 7], 'abs_sum_even_bounds': [2, 14], 'division_by2_exact': True, 'output_bounds': [0, 6], 'Q_pure_no_Board_access_or_mutation': True, 'typed_Board_all_fields_and_update_order_preserved': True, 'logical19_physical21_coefficients_and_features_preserved': True, 'S_quadratic_clamp_and_other_R_features_protected': True, 'canonical_DEV': 'caller bypass; existing model19.h and DEV reference admission preserved', 'native_bit_identity_claimed': False, 'runtime_qualification_claimed': False, 'external_reads': 0, 'compiler_codec_engine_executed_by_transform': 0}

def _sha(data):return hashlib.sha256(data).hexdigest()

def transform_source(source):
    if type(source) is not bytes or len(source)!=INPUT_BYTES or _sha(source)!=INPUT_SHA:
        raise ValueError('exact final E ordering-side shipping source required')
    if source.count(OLD)!=1 or source[AT:AT+len(OLD)]!=OLD:
        raise ValueError('fixed sole Q center construction differs')
    result=source[:AT]+NEW+source[AT+len(OLD):]
    rest=[]
    for old_at,new_at,size,digest in GAPS:
        a=source[old_at:old_at+size];b=result[new_at:new_at+size]
        if a!=b or len(a)!=size or _sha(a)!=digest:
            raise ValueError('center protected gap differs')
        rest.append(a)
    complement=b''.join(rest)
    if len(complement)!=COMPLEMENT_BYTES or _sha(complement)!=COMPLEMENT_SHA:
        raise ValueError('center protected complement differs')
    if result[:AT]+OLD+result[AT+len(NEW):]!=source:
        raise ValueError('center exact full inverse differs')
    if len(result)!=OUTPUT_BYTES or _sha(result)!=OUTPUT_SHA:
        raise ValueError('fixed center candidate differs')
    return result,dict(METADATA)
