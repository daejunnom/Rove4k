"""Pure fixed E legal-square walk after completed-depth token.
Only ap/g headers and invalid-origin skip change; exact64square order stays.
Model/order/search bodies and canonical/DEV paths remain unchanged.
"""
import ast
import hashlib
BEFORE=(8598, 'd0f26c164efb52254fa947a47cf8bb66ed41085ab63706482e2212d9193e09da')
AFTER=(8569, '80b854825d2909e2d3edc1eb2dee946952d492216f9ff91243cb6614b6d13853')
EDITS=((1579, 1579, b'for(L q=0;q<128;q++)if(!(q&0x88)){', b'for(L q=0;q<128;q=q+9&~8){'), (2616, 2608, b'for(L o=0;o<128;o++){if(o&0x88){o+=7;continue;}', b'for(L o=0;o<128;o=o+9&~8){'))
GAPS=((0, 0, 1579, '1ab3039cbc41419f774360e70f5ab7568a1065ff37082a5aae16ce0f31399aae'), (1613, 1605, 1003, '19ef252f3a7ad1655ff86cfbae9a0c45c1e549a50bad3ca587c234a2d6b11e07'), (2663, 2634, 5935, 'eca9912b6fd704d6b0c6a57cf5ee46a706531d664784383f5180a44a82bd73f2'))
METADATA={'stage': 'last-E-square-walk', 'family': 'E', 'input_bytes': 8598, 'input_sha256': 'd0f26c164efb52254fa947a47cf8bb66ed41085ab63706482e2212d9193e09da', 'output_bytes': 8569, 'output_sha256': '80b854825d2909e2d3edc1eb2dee946952d492216f9ff91243cb6614b6d13853', 'raw_delta': -29, 'owned_regions': 2, 'protected_gaps': 3, 'full_inverse': True, 'consumers': ['ap insufficient-material scan', 'g move and attack origin scan'], 'iterator': 'signed int0..119 legal mailbox origins, next=(q+9)&~8, final128', 'legal_square_order_and_continue_early_return_preserved': True, 'fixed_Linux_x86_64_int_domain': True, 'model_19_logical_21_physical_5ordering_3learners_PVS_TT_SMP_bodies_unchanged': True, 'canonical_DEV_automatic_changes': False, 'private_direct_think_contract_changed': False, 'native_identity_claimed': False, 'runtime_claimed_by_transform': False, 'external_reads': 0}
BOOT_BEFORE=(9552, '33633c7ac34e378a3024ffde8026fb12a436deaf49b08933b924cad7067559f1')
BOOT_AFTER=(9523, '9dddd3ff1512a9b5a1864732b06b77cb40b63758613d460af68a552292de0e69')
BOOTSTRAP_METADATA={'input_bytes': 9552, 'input_sha256': '33633c7ac34e378a3024ffde8026fb12a436deaf49b08933b924cad7067559f1', 'output_bytes': 9523, 'output_sha256': '9dddd3ff1512a9b5a1864732b06b77cb40b63758613d460af68a552292de0e69', 'owned_regions': 1, 'protected_gaps': 2, 'full_inverse': True, 'actual_previous_depth_order_keyword_cross_literal_chain_consumed': True, 'source_AST_bytes_exact': True, 'compiler_codec_resources_unchanged': True, 'external_reads': 0}

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()
def _need(value,message):
    if not value:raise ValueError(message)
def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed E cross source required')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'E square walk source region differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    _need(_pin(result)==AFTER,'E square walk output differs')
    return result
def restore_source(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==AFTER,'fixed E square walk source required')
    result=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'E square walk result region differs')
        result=result[:new_at]+old+result[new_at+len(new):]
    _need(_pin(result)==BEFORE and _forward(result)==candidate,'E square walk full inverse differs')
    return result
def transform_source(source):
    candidate=_forward(source)
    _need(restore_source(candidate)==source,'E square walk inverse source differs')
    for old_at,new_at,size,digest in GAPS:
        a=source[old_at:old_at+size];b=candidate[new_at:new_at+size]
        _need(a==b and _pin(a)==(size,digest),'E square walk protected gap differs')
    return candidate,dict(METADATA)
def transform_bootstrap(previous,*,source):
    _need(type(previous)is bytes and _pin(previous)==BOOT_BEFORE,'actual preceding E depth token bootstrap required')
    before=restore_source(source)
    old=b'br'+b'"'*3+before+b'"'*3;new=b'br'+b'"'*3+source+b'"'*3
    _need(previous.count(old)==1 and b'"'*3 not in source and b'\r' not in source,'E square walk literal domain differs')
    calls=[n for n in ast.walk(ast.parse(previous))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==before,'preceding E depth token literal AST differs')
    at=previous.index(old);result=previous[:at]+new+previous[at+len(old):]
    _need(_pin(result)==BOOT_AFTER,'E square walk bootstrap differs')
    _need(result[:at]==previous[:at] and result[at+len(new):]==previous[at+len(old):],'E square walk bootstrap gap differs')
    _need(result[:at]+old+result[at+len(new):]==previous,'E square walk bootstrap inverse differs')
    calls=[n for n in ast.walk(ast.parse(result))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==source,'E square walk literal AST differs')
    return result,dict(BOOTSTRAP_METADATA)
