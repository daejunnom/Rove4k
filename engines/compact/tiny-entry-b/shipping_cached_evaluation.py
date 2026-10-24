"""Pure fixed B shipping reuse of immutable entry raw evaluation.

Apply after singular-depth cleanup; canonical/DEV retain the prior readable
reference spelling and live diagnostics. Actual make/SEE child copies, the
same-position excluded call and root drain/publication keep input s/v stable.
Only hashlib is used. No file, process, recipe or research receipt is read.
"""
import hashlib

_BEFORE=(10409,'85bcdfe488fdd02195669ada95a02e2d2ab3699e677abecfe7fa91ddc68ab9c8')
_AFTER=(10402,'75a081d620af7d966d340d8ffcba5763f37d4df44ab01822d8b178042e0d8faa')
_AT=7015
_OLD=b'int zE=zi-p->s*p->v;'
_NEW=b'int zE=zi-zF;'
_GAPS=(
    (0,0,7015,'bf0971222e3b5c6e4bfbfbf94b0ddbad3a29049651b1a3612e95710b7598947d'),
    (7035,7028,3374,'9a6f0ea9db8413863dbd57d960f1a3bc3e3e4aea57f316ade7789b433b565c19'),
)
_COMPLEMENT=(10389,'811166337067a3fef4ae0b95a9910caf19a999a2b11d7c1aad10841af89bf064')


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Reuse the actual raw int cache in one fixed correction update span."""
    if type(source) is not bytes or _pin(source)!=_BEFORE:
        raise ValueError('fixed B cached-evaluation shipping input differs')
    if source[_AT:_AT+len(_OLD)]!=_OLD or source.count(_OLD)!=1:
        raise ValueError('owned B raw-evaluation correction span differs')
    result=source[:_AT]+_NEW+source[_AT+len(_OLD):]
    if _pin(result)!=_AFTER:
        raise ValueError('fixed B cached-evaluation output differs')
    complement=[]
    for old_at,new_at,length,digest in _GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected B cached-evaluation gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=_COMPLEMENT:
        raise ValueError('protected B cached-evaluation complement differs')
    if result[_AT:_AT+len(_NEW)]!=_NEW or result[:_AT]+_OLD+result[_AT+len(_NEW):]!=source:
        raise ValueError('full B cached-evaluation inverse differs')
    return result,{
        'family':'B','stage':'late-shipping-immutable-entry-raw-evaluation-reuse',
        'input_bytes':_BEFORE[0],'input_sha256':_BEFORE[1],
        'output_bytes':_AFTER[0],'output_sha256':_AFTER[1],
        'raw_delta':-7,'owned_regions':1,'protected_gaps':2,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':_COMPLEMENT[0],
        'protected_complement_sha256':_COMPLEMENT[1],
        'cached_raw_int':'zF=p->s*p->v; not correction-adjusted',
        'cache_reassigned_or_address_taken':False,
        'input_Board_immutable_in_actual_search_call_graph':True,
        'same_position_excluded_and_child_copy_ownership_preserved':True,
        'root_publication_and_drain_bytes_protected':True,
        'correction_guard_clamp_update_and_all_other_search_bytes_protected':True,
        'canonical_DEV':'caller bypass; existing readable reference domain preserved',
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
