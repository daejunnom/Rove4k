"""Pure B shipping cleanup of an unused diagnostic extension decision slot.

Apply after piece-index processing. Canonical/DEV keep the live counter.
Only the decision's depth consumer remains in shipping, so evaluate it once
inside that same int addition and remove the empty diagnostic condition.
Only hashlib is used; no file, process, recipe or research receipt is read.
"""
import hashlib

_BEFORE=(10421,'792a8b50f307aeac98415636d280a076f1ba8ea68e7eb4f43ec9dff514299e85')
_AFTER=(10409,'85bcdfe488fdd02195669ada95a02e2d2ab3699e677abecfe7fa91ddc68ab9c8')
_AT=6409
_OLD=b'int zH=yr&&m==tt,z3=a-1+zH;if(zH){}'
_NEW=b'int z3=a-1+(yr&&m==tt);'
_GAPS=(
    (0,0,6409,'330a1fab0bc40dff63cb0f4d67531ab5b0fdb6194297600f5aca888a08e7723d'),
    (6444,6432,3977,'db5a59823a8e6aa96082ed5d5b6d2844eb220000f24a260e76d9d71c1b88121b'),
)
_COMPLEMENT=(10386,'662e47f7f732ebe48572398d134818e39afa23071428676bd5dcdf08a62542ea')


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Replay one fixed dead-instrumentation span and its existing contract."""
    if type(source) is not bytes or _pin(source)!=_BEFORE:
        raise ValueError('fixed B singular-depth shipping input differs')
    if source[_AT:_AT+len(_OLD)]!=_OLD or source.count(_OLD)!=1:
        raise ValueError('owned B diagnostic decision/depth span differs')
    result=source[:_AT]+_NEW+source[_AT+len(_OLD):]
    if _pin(result)!=_AFTER:
        raise ValueError('fixed B singular-depth output differs')
    complement=[]
    for old_at,new_at,length,digest in _GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected B singular-depth gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=_COMPLEMENT:
        raise ValueError('protected B singular-depth complement differs')
    if result[_AT:_AT+len(_NEW)]!=_NEW or result[:_AT]+_OLD+result[_AT+len(_NEW):]!=source:
        raise ValueError('full B singular-depth inverse differs')
    return result,{
        'family':'B','stage':'late-shipping-dead-extension-instrumentation-cleanup',
        'input_bytes':_BEFORE[0],'input_sha256':_BEFORE[1],
        'output_bytes':_AFTER[0],'output_sha256':_AFTER[1],
        'raw_delta':-12,'owned_regions':1,'protected_gaps':2,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':_COMPLEMENT[0],
        'protected_complement_sha256':_COMPLEMENT[1],
        'temporary_has_one_meaningful_depth_consumer':True,
        'empty_diagnostic_condition_removed':True,
        'decision_type':'int0or1','decision_evaluation_count':1,
        'short_circuit_and_int_depth_addition_preserved':True,
        'ordinary_local_values_without_side_effects':True,
        'all_four_recursive_depth_consumers_byte_protected':True,
        'model_search_learner_TT_pool_protocol_policy_bytes_protected':True,
        'canonical_DEV':'caller bypass; diagnostic counter remains live',
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
