"""Pure fixed E shipping ordering reuse of the generated mover side.

Apply after capture metadata. R receives only the same Board's generated
moves, whose nonzero origin piece has side p->s. Read the original pawn
before make/promotion. Root drain and private children preserve the Board.
Canonical/DEV and E19 coefficients stay in their existing reference domain.
Only hashlib is used: no files, processes, recipes or research receipts.
"""
import hashlib

INPUT=(10210,'060847dbe19b898d5a7a0f7b49ee35b2338529abb2b63073798453db227ee147')
OUTPUT=(10200,'6d336854f38c3a1aaf2b3facb7487aa3ece687f5280a5e9315eb08b2425bf329')
EDITS=(
    (4023,4023,b'i=p->b[d],a=abs(i)',b'a=abs(p->b[d])'),
    (4304,4300,b'*(i<0?-1:1)',b'*p->s'),
)
GAPS=(
    (0,0,4023,'e56d298316bffe917fbc800c85ba013e8fbd1adf667873c6603566634468ece3'),
    (4041,4037,263,'58489f2e97884e6776f8eebbc82735b7f14c3b5db9374747fed260b24ca9d692'),
    (4315,4305,5895,'d4a8dac9b9d703e6d0cbdf5176448aeeb6927b2d341227601140afcea8f7e7d4'),
)
COMPLEMENT=(10181,'bd4aca12bb100387b53686b784405b251b37e0850bcf0fd225514eddcc082085')


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Replay two owned literals and verify the existing byte/inverse contract."""
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('fixed E ordering-side shipping input differs')
    candidate=source
    for old_at,new_at,old,new in reversed(EDITS):
        if source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('owned E ordering-side literal differs')
        candidate=candidate[:old_at]+new+candidate[old_at+len(old):]
    if _pin(candidate)!=OUTPUT:
        raise ValueError('fixed E ordering-side output differs')
    complement=[]
    for old_at,new_at,length,digest in GAPS:
        old=source[old_at:old_at+length];new=candidate[new_at:new_at+length]
        if old!=new or _pin(old)!=(length,digest):
            raise ValueError('protected E ordering-side gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=COMPLEMENT:
        raise ValueError('protected E ordering-side complement differs')
    inverse=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('fixed E ordering-side inverse literal differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:
        raise ValueError('full E ordering-side inverse differs')
    return candidate,{
        'family':'E','stage':'late-shipping-generated-mover-side-reuse',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-10,'owned_regions':2,'protected_gaps':3,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':COMPLEMENT[0],
        'protected_complement_sha256':COMPLEMENT[1],
        'actual_call_contract':'R consumes same-Board generated moves; origin is nonzero own-side',
        'side_domain':[-1,1],'origin_int8_to_int_promotion_preserved':True,
        'original_pawn_EP_and_promotion_before_make':True,
        'root_drain_private_child_Board_ownership_preserved':True,
        'E19_coefficients_and_other_ordering_features_protected':True,
        'search_learners_TT_input_pool_bytes_protected':True,
        'canonical_DEV':'caller bypass; existing readable reference domain preserved',
        'native_bit_identity_claimed':False,'runtime_qualification_claimed':False,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
