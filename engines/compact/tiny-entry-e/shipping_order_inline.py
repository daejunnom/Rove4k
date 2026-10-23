"""Pure current E sole-caller ordering inline after the keyword stage.
Fixed source and literal inverse keep all preceding production guards live.
"""
import ast
import hashlib
BEFORE=(8702, 'eb34a717b3bdd6e5b96a13ecdbce224c6ac1c8ef7b56a057f6325e8619410af7')
AFTER=(8616, 'c03884ea1badbdb3357d39998b3e49973ffdc921ba122d99e14c8ea63a146b20')
EDITS=((1167, 1167, b'static L r(const E*p,Y m){L d=FROM(m),f=TO(m),a=abs(p->b[d]),v=abs(p->b[f]),j=PROMO(m);if(a==1&&f==p->e&&!v)v=1;L s=qi[19]*(Q(f)-Q(d));if(v)s+=qi[16]*qi[v]+qi[17]*qi[a];if(j)s+=qi[18]*(qi[j]-qi[1]);if(a==1)s+=qi[20]*((f>>4)-(d>>4))*p->s;J s;}', b''), (4681, 4439, b'for(L i=0;i<z;i++){Y m=B[i];L o=FROM(m),P=TO(m),R=s(p->b[o]);y[i]=m==j?1000000:m&8?500000:w->zC[o][P]+w->an[f][R]+(L)((m*37u+w->id*19u)%17);if(PROMO(m))y[i]+=400000+PROMO(m)*1000;y[i]+=r(p,m);}', b'for(L i=0;i<z;i++){Y m=B[i];L o=FROM(m),P=TO(m),R=s(p->b[o]),a=abs(R-6),v=abs(p->b[P]),k=PROMO(m);if(a==1&&P==p->e&&!v)v=1;y[i]=(m==j?1000000:m&8?500000:w->zC[o][P]+w->an[f][R]+(L)((m*37u+w->id*19u)%17))+qi[19]*(Q(P)-Q(o));if(v)y[i]+=qi[16]*qi[v]+qi[17]*qi[a];if(k)y[i]+=400000+k*1000+qi[18]*(qi[k]-qi[1]);if(a==1)y[i]+=qi[20]*((P>>4)-(o>>4))*p->s;}'))
GAPS=((0, 0, 1167, '6b0b6cb39de151784030cddda3961ea886bffc133e52004e54378aab48faacd0'), (1409, 1167, 3272, 'b2b05635b3bf542b8aeb0a28994fdbbdaa3708af84c7a8503167f90ddbaac2b0'), (4874, 4788, 3828, 'c7720a3cf0f11f7f9b8c1ea9f0686cf41ee62f4c22db7d2fd785646d16f292ad'))
METADATA={'stage': 'last-E-sole-caller-order-inline', 'family': 'E', 'input_bytes': 8702, 'input_sha256': 'eb34a717b3bdd6e5b96a13ecdbce224c6ac1c8ef7b56a057f6325e8619410af7', 'output_bytes': 8616, 'output_sha256': 'c03884ea1badbdb3357d39998b3e49973ffdc921ba122d99e14c8ea63a146b20', 'raw_delta': -86, 'owned_regions': 2, 'protected_gaps': 3, 'full_inverse': True, 'logical_coefficients': 19, 'physical_slots': 21, 'all_coefficients_independently_consumed': True, 'Q_S_setter_pool_and_model_fields_unchanged': True, 'ordering_features': 5, 'actual_sole_caller_role': 'h generated own-side pseudo-move preordering before make', 'source_model_or_search_policy_change': False, 'native_entire_bytes_equal': False, 'native_bytes_before': 18576, 'native_bytes_after': 22672, 'native_codegen_or_timing_may_change': True, 'promotion_int_type_note': 'PROMO unsigned expression becomes int local k; fixed generated promotion2..5 and score[-66476,1429040] prove same values', 'DEV': 'caller bypasses all shipping transformations; old qualified diagnostic source/native remain distinct', 'external_reads': 0, 'runtime_claimed_by_transform': False}
BOOT_BEFORE=(9656, 'dcae86bcd4e6cb6fe324a09186e100920cf32f161fc39e610ebd005304feb8f0')
BOOT_AFTER=(9570, '0448cdb281d9cb37d7e448db18317b6db30f85a0db4bf676bf5ea83f28620dd3')
BOOTSTRAP_METADATA={'input_bytes': 9656, 'input_sha256': 'dcae86bcd4e6cb6fe324a09186e100920cf32f161fc39e610ebd005304feb8f0', 'output_bytes': 9570, 'output_sha256': '0448cdb281d9cb37d7e448db18317b6db30f85a0db4bf676bf5ea83f28620dd3', 'owned_regions': 1, 'protected_gaps': 2, 'full_inverse': True, 'actual_previous_keyword_and_cross_literal_chain_consumed': True, 'source_AST_bytes_exact': True, 'compiler_codec_resources_unchanged': True, 'external_reads': 0}

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()
def _need(value,message):
    if not value:raise ValueError(message)
def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed E cross source required')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'E order inline source region differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    _need(_pin(result)==AFTER,'E order inline output differs')
    return result
def restore_source(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==AFTER,'fixed E order inline source required')
    result=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'E order inline result region differs')
        result=result[:new_at]+old+result[new_at+len(new):]
    _need(_pin(result)==BEFORE and _forward(result)==candidate,'E order inline full inverse differs')
    return result
def transform_source(source):
    candidate=_forward(source)
    _need(restore_source(candidate)==source,'E order inline inverse source differs')
    for old_at,new_at,size,digest in GAPS:
        a=source[old_at:old_at+size];b=candidate[new_at:new_at+size]
        _need(a==b and _pin(a)==(size,digest),'E order inline protected gap differs')
    return candidate,dict(METADATA)
def transform_bootstrap(previous,*,source):
    _need(type(previous)is bytes and _pin(previous)==BOOT_BEFORE,'actual preceding E keyword bootstrap required')
    before=restore_source(source)
    old=b'br'+b'"'*3+before+b'"'*3;new=b'br'+b'"'*3+source+b'"'*3
    _need(previous.count(old)==1 and b'"'*3 not in source and b'\r' not in source,'E order inline literal domain differs')
    calls=[n for n in ast.walk(ast.parse(previous))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==before,'preceding E keyword literal AST differs')
    at=previous.index(old);result=previous[:at]+new+previous[at+len(old):]
    _need(_pin(result)==BOOT_AFTER,'E order inline bootstrap differs')
    _need(result[:at]==previous[:at] and result[at+len(new):]==previous[at+len(old):],'E order inline bootstrap gap differs')
    _need(result[:at]+old+result[at+len(new):]==previous,'E order inline bootstrap inverse differs')
    calls=[n for n in ast.walk(ast.parse(result))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==source,'E order inline literal AST differs')
    return result,dict(BOOTSTRAP_METADATA)
