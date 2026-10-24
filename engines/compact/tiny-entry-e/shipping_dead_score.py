"""Pure fixed full-shipping E dead-score removal, after legal-square walk.
Only an unconsumed Worker field, reset/store and unused return binding change.
The recursive search call, completed best/depth commits and all other bytes remain.
"""
import ast
import hashlib
BEFORE=(8569, '80b854825d2909e2d3edc1eb2dee946952d492216f9ff91243cb6614b6d13853')
AFTER=(8549, '3f007f6a38f36133fa7b54b0e2b0cc6ef051dcc19a1167c14529dca028c8b0b1')
EDITS=((518, 518, b'L id,C,l;', b'L id,C;'), (5749, 5747, b'w->l=0;', b''), (5826, 5817, b'L l=h(w,p,C,-30000,30000,0,6,&H);', b'h(w,p,C,-30000,30000,0,6,&H);'), (5922, 5909, b'w->l=l;', b''))
GAPS=((0, 0, 518, '614db2cf50b3952c5d5006de4613bc043662a24864c7004bd684a38c39a0a9dc'), (527, 525, 5222, '7a1d98f756a0e57952a616ca780b419321353335443b2fca99b361461a34d89b'), (5756, 5747, 70, 'cb22a91c17ddc21b5bdd7d4d28930bdb7cae38c92d20ad77a5176b82aff09148'), (5859, 5846, 63, '89da0d039b0a3553c4eff04ba85fdd08348eb3b0c201e78211a407dd259e0a93'), (5929, 5909, 2640, '9dd8e1e41fc12e1fc6d501c339b3f2272778672666534c40c9fd9b41c43eaeec'))
METADATA={'stage': 'late-full-E-unconsumed-score', 'input': (8569, '80b854825d2909e2d3edc1eb2dee946952d492216f9ff91243cb6614b6d13853'), 'output': (8549, '3f007f6a38f36133fa7b54b0e2b0cc6ef051dcc19a1167c14529dca028c8b0b1'), 'raw_delta': -20, 'owned_regions': 4, 'protected_gaps': 5, 'full_inverse': True, 'closed_shipping_domain': 'Worker l has only reset/store; selection consumes completed depth C and best H or legal fallback', 'search_call_and_arguments_preserved': True, 'model_19_logical_21_physical_5ordering_3learners_PVS_TT_SMP_bytes_unchanged': True, 'canonical_DEV_automatic_changes': False, 'native_identity_claimed': False, 'runtime_claimed_by_transform': False, 'external_reads': 0}
BOOT_BEFORE=(10539, '3474857197bd6121020c0e2cb82fafce6112a571b2821a4ff1f782844c25071f')
BOOT_AFTER=(10519, 'b8ee01738e9eb029760306be342417d659f660dfd109d91ed8c56709a7489157')

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def _need(value,message):
    if not value:raise ValueError(message)

def _rewrite(source,inverse=False):
    _need(type(source)is bytes and _pin(source)==(AFTER if inverse else BEFORE),'fixed E dead-score source required')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        at,before,after=(new_at,new,old)if inverse else(old_at,old,new)
        _need(source[at:at+len(before)]==before,'E dead-score owned region differs')
        result=result[:at]+after+result[at+len(before):]
    _need(_pin(result)==(BEFORE if inverse else AFTER),'E dead-score output differs')
    return result

def restore_source(source):return _rewrite(source,True)

def transform_source(source):
    result=_rewrite(source)
    _need(restore_source(result)==source,'E dead-score full inverse differs')
    for a,b,n,h in GAPS:
        _need(source[a:a+n]==result[b:b+n] and _pin(source[a:a+n])==(n,h),'E dead-score protected gap differs')
    return result,dict(METADATA)

def _source_call(tree,expected):
    calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='memoryview']
    _need(len(calls)==1 and len(calls[0].args)==1 and ast.literal_eval(calls[0].args[0])==expected,'E dead-score current owner literal AST differs')
    return calls[0]

def transform_bootstrap(previous,*,source):
    _need(type(previous)is bytes and _pin(previous)==BOOT_BEFORE,'actual preceding E square/compiler-group bootstrap required')
    before=restore_source(source)
    old=b'br'+b'"'*3+before+b'"'*3;new=b'br'+b'"'*3+source+b'"'*3
    _need(previous.count(old)==1 and b'"'*3 not in source and b'\r' not in source,'E dead-score literal domain differs')
    previous_tree=ast.parse(previous);old_call=_source_call(previous_tree,before)
    at=previous.index(old);result=previous[:at]+new+previous[at+len(old):]
    _need(_pin(result)==BOOT_AFTER,'E dead-score bootstrap differs')
    _need(result[:at]==previous[:at] and result[at+len(new):]==previous[at+len(old):],'E dead-score bootstrap protected gap differs')
    _need(result[:at]+old+result[at+len(new):]==previous,'E dead-score bootstrap full inverse differs')
    result_tree=ast.parse(result);new_call=_source_call(result_tree,source)
    old_call.args[0].value=new_call.args[0].value=b'__E_SOURCE_LITERAL__'
    _need(ast.dump(previous_tree,include_attributes=False)==ast.dump(result_tree,include_attributes=False),'E dead-score non-source AST differs')
    return result,{'input':BOOT_BEFORE,'output':BOOT_AFTER,'owned_regions':1,'protected_gaps':2,'full_inverse':True,
                   'actual_square_depth_order_keyword_cross_and_compiler_group_chain_consumed':True,
                   'source_AST_bytes_exact':True,'all_non_source_AST_and_bytes_equal':True,'external_reads':0}
