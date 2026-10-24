"""Pure B shipping replay: inline the private piece-plus-six index helper.

Apply after maintained history-depth processing; canonical/DEV bypass it.
The two int8_t arguments are promoted to int and evaluated once, retaining
the full signed-piece index domain0..12, black king0 and root neutral6.
Only hashlib is used. No file, process, recipe or research receipt is read.
"""
import hashlib

_BEFORE=(10451,'67603c505eec2377c4c4d96f19caf084178c104e44bd5d1aabed861341b55358')
_AFTER=(10421,'792a8b50f307aeac98415636d280a076f1ba8ea68e7eb4f43ec9dff514299e85')
_EDITS=(
    (4449,4449,b'static int J(int p){return p+6;}',b''),
    (5910,5878,b'J(p->b[zJ])',b'(p->b[zJ]+6)'),
    (6387,6356,b'J(q.b[to])',b'(q.b[to]+6)'),
)
_GAPS=(
    (0,0,4449,'96fda474afe46d1a11019cf4f132936963aacce630e25998bfdc057e2ebfecaf'),
    (4481,4449,1429,'e3baea066d50b3f44e0857c980af8247d11974d60b2af23b42b4df88dcce2d7d'),
    (5921,5890,466,'2090a822e53df3a74787f1daa60ba0106c7e660263ba02c0ce438cfdbc855666'),
    (6397,6367,4054,'e6d4f0f743eb2b1fe0705e69149db376acd933dac208c5ed6b2bd86bbcac336b'),
)
_COMPLEMENT=(10398,'80b5729870ff71b9f8541064dd50ee00a9a13f542cdf71c2f4a098656951dcbf')


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Replay the fixed three spans and check all other source bytes."""
    if type(source) is not bytes or _pin(source)!=_BEFORE:
        raise ValueError('fixed B piece-index shipping input differs')
    parts=[];cursor=written=0
    for old_at,new_at,old,new in _EDITS:
        if old_at<cursor or source[old_at:old_at+len(old)]!=old or source.count(old)!=1:
            raise ValueError('owned B piece-index definition/call span differs')
        gap=source[cursor:old_at]
        if written+len(gap)!=new_at:
            raise ValueError('fixed B piece-index output position differs')
        parts.extend((gap,new));written=new_at+len(new);cursor=old_at+len(old)
    parts.append(source[cursor:]);result=b''.join(parts)
    if _pin(result)!=_AFTER:
        raise ValueError('fixed B piece-index output differs')
    complement=[]
    for old_at,new_at,length,digest in _GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected B piece-index gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=_COMPLEMENT:
        raise ValueError('protected B piece-index complement differs')
    inverse=result
    for old_at,new_at,old,new in reversed(_EDITS):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('fixed B piece-index inverse position differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:
        raise ValueError('full B piece-index inverse differs')
    return result,{
        'family':'B','stage':'late-shipping-private-piece-index-inline',
        'input_bytes':_BEFORE[0],'input_sha256':_BEFORE[1],
        'output_bytes':_AFTER[0],'output_sha256':_AFTER[1],
        'raw_delta':-30,'owned_regions':3,'protected_gaps':4,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':_COMPLEMENT[0],
        'protected_complement_sha256':_COMPLEMENT[1],
        'sole_private_definition_and_two_calls':True,
        'argument_evaluation_count':1,'int8_t_promotion_and_int_addition_preserved':True,
        'valid_piece_range':[-6,6],'index_range':[0,12],
        'black_king_index':0,'empty_and_root_neutral_index':6,'white_king_index':12,
        'zw13x13_consumers_and_recursive_context_byte_protected':True,
        'model_search_learner_TT_pool_protocol_bytes_protected':True,
        'canonical_DEV':'caller bypass','external_reads':0,
        'compiler_codec_engine_executed_by_transform':0,
    }
