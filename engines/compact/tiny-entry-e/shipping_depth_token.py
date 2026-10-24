"""Pure fixed E completed-depth job-token representation after order inline.
Own C=-1 underqj is unclaimed; worker claims0 underqj before think.
wNULL startup sentinel, flush/drain and partial joins stay unchanged.
Private direct think callers must seed0; canonical/DEV bypass this stage.
"""
import ast
import hashlib
BEFORE=(8616, 'c03884ea1badbdb3357d39998b3e49973ffdc921ba122d99e14c8ea63a146b20')
AFTER=(8598, 'd0f26c164efb52254fa947a47cf8bb66ed41085ab63706482e2212d9193e09da')
EDITS=((5770, 5770, b'w->a5=0;w->C=0;w->l=0;', b'w->a5=0;w->l=0;'), (6076, 6069, b'static unsigned qd;', b''), (6604, 6578, b'ai*w=0;unsigned a=0;', b'ai*w=0,*a=p;'), (6704, 6670, b'while(a==qd&&!qm)', b'while(a->C>=0&&!qm)'), (6760, 6728, b'w=p;a=qd;', b'w=a;w->C=0;'), (7798, 7768, b'qk=2;qd++;', b'qk=2;qr->C=qr[1].C=-1;'))
GAPS=((0, 0, 5770, '70069204792d0ba5d4f6e713db913f7d62b848c8b2a2b567078dd74846376673'), (5792, 5785, 284, '9f112f824a970ac0a4aff74a05031fccf584b4a50ce8b5abef6ac7a841ba5357'), (6095, 6069, 509, '6e8f828644924a13cc2b11541ea308e4b15e8114e7759a8ce2960ed1397a14dc'), (6624, 6590, 80, '9a3c8abac19f9e84b752bc16e75b56e763b8c273223c5e25b28de2fede40419e'), (6721, 6689, 39, '2db75265c2eb7155de557c4303b1197fc74ab4768a44e348bc6a26c01633116a'), (6769, 6739, 1029, '3124f98bda0a87f3c1037b5079b2e15bfb5b377730d8540e4edde5a70dc6b2e6'), (7808, 7790, 808, '8b5fcc203356921c7a79e36066521723417f03bdc599ae2d5b9a669f5f73a228'))
METADATA={'stage': 'last-E-completed-depth-job-token', 'family': 'E', 'input_bytes': 8616, 'input_sha256': 'c03884ea1badbdb3357d39998b3e49973ffdc921ba122d99e14c8ea63a146b20', 'output_bytes': 8598, 'output_sha256': 'd0f26c164efb52254fa947a47cf8bb66ed41085ab63706482e2212d9193e09da', 'raw_delta': -18, 'roles': 6, 'protected_gaps': 7, 'full_inverse': True, 'job_token': 'ai.C -1 unclaimed,0 claimed/no finished depth,1..126 completed result', 'shipping_C_caller_domain': 'Unique worker A claims0 underqj before C(w,&ql); direct private think callers must seed0', 'w_null_startup_and_stable_owner_preserved': True, 'GO_both_tokens_published_under_mutex_after_drain': True, 'qk_last_result_flush_and_partial_created_joins_preserved': True, 'model_ordering_TT_learner_PVS_bodies_unchanged': True, 'canonical_DEV_automatic_changes': False, 'private_direct_think_contract_changed': True, 'native_identity_claimed': False, 'runtime_claimed_by_transform': False, 'external_reads': 0}
BOOT_BEFORE=(9570, '0448cdb281d9cb37d7e448db18317b6db30f85a0db4bf676bf5ea83f28620dd3')
BOOT_AFTER=(9552, '33633c7ac34e378a3024ffde8026fb12a436deaf49b08933b924cad7067559f1')
BOOTSTRAP_METADATA={'input_bytes': 9570, 'input_sha256': '0448cdb281d9cb37d7e448db18317b6db30f85a0db4bf676bf5ea83f28620dd3', 'output_bytes': 9552, 'output_sha256': '33633c7ac34e378a3024ffde8026fb12a436deaf49b08933b924cad7067559f1', 'owned_regions': 1, 'protected_gaps': 2, 'full_inverse': True, 'actual_previous_order_keyword_cross_literal_chain_consumed': True, 'source_AST_bytes_exact': True, 'compiler_codec_resources_unchanged': True, 'external_reads': 0}

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()
def _need(value,message):
    if not value:raise ValueError(message)
def _forward(source):
    _need(type(source)is bytes and _pin(source)==BEFORE,'fixed E cross source required')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        _need(source[old_at:old_at+len(old)]==old,'E depth token source region differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    _need(_pin(result)==AFTER,'E depth token output differs')
    return result
def restore_source(candidate):
    _need(type(candidate)is bytes and _pin(candidate)==AFTER,'fixed E depth token source required')
    result=candidate
    for old_at,new_at,old,new in reversed(EDITS):
        _need(candidate[new_at:new_at+len(new)]==new,'E depth token result region differs')
        result=result[:new_at]+old+result[new_at+len(new):]
    _need(_pin(result)==BEFORE and _forward(result)==candidate,'E depth token full inverse differs')
    return result
def transform_source(source):
    candidate=_forward(source)
    _need(restore_source(candidate)==source,'E depth token inverse source differs')
    for old_at,new_at,size,digest in GAPS:
        a=source[old_at:old_at+size];b=candidate[new_at:new_at+size]
        _need(a==b and _pin(a)==(size,digest),'E depth token protected gap differs')
    return candidate,dict(METADATA)
def transform_bootstrap(previous,*,source):
    _need(type(previous)is bytes and _pin(previous)==BOOT_BEFORE,'actual preceding E order inline bootstrap required')
    before=restore_source(source)
    old=b'br'+b'"'*3+before+b'"'*3;new=b'br'+b'"'*3+source+b'"'*3
    _need(previous.count(old)==1 and b'"'*3 not in source and b'\r' not in source,'E depth token literal domain differs')
    calls=[n for n in ast.walk(ast.parse(previous))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==before,'preceding E order inline literal AST differs')
    at=previous.index(old);result=previous[:at]+new+previous[at+len(old):]
    _need(_pin(result)==BOOT_AFTER,'E depth token bootstrap differs')
    _need(result[:at]==previous[:at] and result[at+len(new):]==previous[at+len(old):],'E depth token bootstrap gap differs')
    _need(result[:at]+old+result[at+len(new):]==previous,'E depth token bootstrap inverse differs')
    calls=[n for n in ast.walk(ast.parse(result))if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='communicate']
    _need(len(calls)==1 and ast.literal_eval(calls[0].args[0])==source,'E depth token literal AST differs')
    return result,dict(BOOTSTRAP_METADATA)
