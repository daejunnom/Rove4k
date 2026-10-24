"""Pure fixed B shipping adjacent HCE int declaration merge.

Apply after cached-evaluation reuse. Same automatic int declarators and
initializer full-expressions retain lexical order and scope. Canonical/DEV
bypass the shipping stage. Only hashlib is used; no file, process, compiler,
codec, recipe or research receipt is read by the maintained transform.
"""
import hashlib

_BEFORE=(10402,'75a081d620af7d966d340d8ffcba5763f37d4df44ab01822d8b178042e0d8faa')
_AFTER=(10394,'61f6dabc7b171c864c3d3511906799e13b638023d96a537c1fa15a05a0648c63')
_REGIONS=(
    (1127,1127,b';int j=',b',j='),
    (1157,1153,b';int m=',b',m='),
)
_GAPS=(
    (0,0,1127,'c46567d7226ee6f2df3ccf054299495a28a35d49ff778839e5bd123bad5e8e70'),
    (1134,1130,23,'ed68d54c36b4a389165194cd84eda2f83ad0b2a63edda7e1915c37285bd3913e'),
    (1164,1156,9238,'7ef91eb312b6895c20508b0227669723efdfb37dfb12e7b4a349a7793bbd3cd3'),
)
_COMPLEMENT=(10388,'d2b259bae7f5a4cf2cb8c0ee0b1c0d4390a44db3cda8024ebc773a2b59c6ce18')


def _pin(data):return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Merge only the two exact same-int HCE declaration separators."""
    if type(source) is not bytes or _pin(source)!=_BEFORE:
        raise ValueError('fixed B HCE-declaration shipping input differs')
    parts=[];previous=0
    for old_at,new_at,old,new in _REGIONS:
        if old_at<previous or source[old_at:old_at+len(old)]!=old:
            raise ValueError('owned B HCE declaration span differs')
        parts.extend((source[previous:old_at],new));previous=old_at+len(old)
    parts.append(source[previous:]);result=b''.join(parts)
    if _pin(result)!=_AFTER:
        raise ValueError('fixed B HCE-declaration output differs')
    complement=[]
    for old_at,new_at,length,digest in _GAPS:
        old=source[old_at:old_at+length];new=result[new_at:new_at+length]
        if old!=new or hashlib.sha256(old).hexdigest()!=digest:
            raise ValueError('protected B HCE-declaration gap differs')
        complement.append(old)
    if _pin(b''.join(complement))!=_COMPLEMENT:
        raise ValueError('protected B HCE-declaration complement differs')
    inverse=result
    for old_at,new_at,old,new in reversed(_REGIONS):
        if inverse[new_at:new_at+len(new)]!=new:
            raise ValueError('B HCE-declaration inverse span differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if inverse!=source:
        raise ValueError('full B HCE-declaration inverse differs')
    return result,{
        'family':'B','stage':'late-shipping-HCE-adjacent-int-declarations',
        'input_bytes':_BEFORE[0],'input_sha256':_BEFORE[1],
        'output_bytes':_AFTER[0],'output_sha256':_AFTER[1],
        'raw_delta':-8,'owned_regions':2,'protected_gaps':3,
        'full_inverse':True,'all_gaps_equal':True,
        'protected_complement_bytes':_COMPLEMENT[0],
        'protected_complement_sha256':_COMPLEMENT[1],
        'same_automatic_int_type_and_declarator_scope':True,
        'initializer_full_expressions_order_dependencies_preserved':True,
        'pure_bounded_integer_abs_and_immutable_qi_reads_only':True,
        'formulas_coefficients_calls_and_all_other_bytes_preserved':True,
        'canonical_DEV':'caller bypass; unchanged readable reference domain',
        'general_macro_source_or_traceback_equivalence_claimed':False,
        'native_identity_is_separate_actual_compiler_evidence':True,
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
