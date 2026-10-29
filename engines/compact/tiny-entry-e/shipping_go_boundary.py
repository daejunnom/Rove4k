"""Pure fixed E sole-GO function boundary removal, after dead-score removal.
The complete407-byte body moves byte-identically into its sole exact-go caller's
nested block. No parser/search/state expression or previous guard is weakened.
"""
import ast
import hashlib
BEFORE=(8549, '3f007f6a38f36133fa7b54b0e2b0cc6ef051dcc19a1167c14529dca028c8b0b1')
AFTER=(8526, 'c0b01df4c8a330fce2fdfe28a15feb885ce1155e3dddf59b739c0c39f5652b75')
EDITS=((7368, 7368, b'static void w(void){j();W a=-1,d=0,S=0;for(char*t=nt();t;t=nt()){if((*t==\'w\'||*t==\'b\')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){W n=y(nt());if((*t==\'w\')==(ql.s>0)){if(t[1]==\'t\')a=n;else d=n;}}}if(~a){S=a/30+(d>86400000?86400000:d)*3/4;if(S>a/5)S=a/5;if(!S)S=1;}else S=1000;qc=u()+(S>86400000?86400000:S);atomic_store(&qp,0);pthread_mutex_lock(&qj);qk=2;qr->C=qr[1].C=-1;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);}', b''), (8384, 7956, b'w();', b'{j();W a=-1,d=0,S=0;for(char*t=nt();t;t=nt()){if((*t==\'w\'||*t==\'b\')&&(!strcmp(t+1,"time")||!strcmp(t+1,"inc"))){W n=y(nt());if((*t==\'w\')==(ql.s>0)){if(t[1]==\'t\')a=n;else d=n;}}}if(~a){S=a/30+(d>86400000?86400000:d)*3/4;if(S>a/5)S=a/5;if(!S)S=1;}else S=1000;qc=u()+(S>86400000?86400000:S);atomic_store(&qp,0);pthread_mutex_lock(&qj);qk=2;qr->C=qr[1].C=-1;pthread_cond_broadcast(&qb);pthread_mutex_unlock(&qj);}'))
GAPS=((0, 0, 7368, '2bc0dd20ba3ab39b32af132d9a6c60889d5559cfeb2dd394fd20695c7da839f1'), (7796, 7368, 588, 'cbd05bef77a73bf7ac4979ba0f524bd10fd99ecf1d29de81cb1363d327a986d9'), (8388, 8365, 161, '226f8ef8a71c6701e37f0a6152451350aaacd517a8d152b3aebf7e45969d6cad'))
METADATA={'stage': 'late-full-E-sole-GO-boundary', 'input': (8549, '3f007f6a38f36133fa7b54b0e2b0cc6ef051dcc19a1167c14529dca028c8b0b1'), 'output': (8526, 'c0b01df4c8a330fce2fdfe28a15feb885ce1155e3dddf59b739c0c39f5652b75'), 'raw_delta': -23, 'owned_regions': 2, 'protected_gaps': 3, 'full_inverse': True, 'GO_body_bytes': 407, 'GO_body_sha256': '75eb7519720fbe135882317fcbce0c3c708ce9463ccb141769c3166ee4b9afee', 'body_byte_identical': True, 'sole_caller': 'main exact go branch, complete w(); expression replaced by nested block', 'scope': 'a,d,S,t,n remain block-local; main a/d/V shutdown ownership and free-name bindings preserved', 'clock_token_cursor_drain_deadline_mutex_publication_broadcast_unchanged': True, 'all_other_TU_bytes_model_ordering_TT_learners_search_stop_unchanged': True, 'canonical_DEV_automatic_changes': False, 'native_identity_claimed_by_transform': False, 'runtime_claimed_by_transform': False, 'debug_stack_frame_and_timing_equivalence_claimed': False, 'external_reads': 0}
BOOT_BEFORE=(10519, 'b8ee01738e9eb029760306be342417d659f660dfd109d91ed8c56709a7489157')
BOOT_AFTER=(10496, '31b5296ff8474490d9f07a27872823845e1e58487139fb84b7d122d74625b463')

def _pin(data):return len(data),hashlib.sha256(data).hexdigest()

def _need(value,message):
    if not value:raise ValueError(message)

def _rewrite(source,inverse=False):
    _need(type(source)is bytes and _pin(source)==(AFTER if inverse else BEFORE),'fixed E sole-GO boundary source required')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        at,before,after=(new_at,new,old)if inverse else(old_at,old,new)
        _need(source[at:at+len(before)]==before,'E sole-GO boundary owned region differs')
        result=result[:at]+after+result[at+len(before):]
    _need(_pin(result)==(BEFORE if inverse else AFTER),'E sole-GO boundary output differs')
    return result

def restore_source(source):return _rewrite(source,True)

def transform_source(source):
    result=_rewrite(source)
    _need(restore_source(result)==source,'E sole-GO boundary full inverse differs')
    for a,b,n,h in GAPS:
        _need(source[a:a+n]==result[b:b+n] and _pin(source[a:a+n])==(n,h),'E sole-GO boundary protected gap differs')
    return result,dict(METADATA)

def _source_call(tree,expected):
    calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='memoryview']
    _need(len(calls)==1 and len(calls[0].args)==1 and ast.literal_eval(calls[0].args[0])==expected,'E sole-GO boundary current owner literal AST differs')
    return calls[0]

def transform_bootstrap(previous,*,source):
    _need(type(previous)is bytes and _pin(previous)==BOOT_BEFORE,'actual preceding E dead-score/compiler-group bootstrap required')
    before=restore_source(source)
    old=b'br'+b'"'*3+before+b'"'*3;new=b'br'+b'"'*3+source+b'"'*3
    _need(previous.count(old)==1 and b'"'*3 not in source and b'\r' not in source,'E sole-GO boundary literal domain differs')
    previous_tree=ast.parse(previous);old_call=_source_call(previous_tree,before)
    at=previous.index(old);result=previous[:at]+new+previous[at+len(old):]
    _need(_pin(result)==BOOT_AFTER,'E sole-GO boundary bootstrap differs')
    _need(result[:at]==previous[:at] and result[at+len(new):]==previous[at+len(old):],'E sole-GO boundary bootstrap protected gap differs')
    _need(result[:at]+old+result[at+len(new):]==previous,'E sole-GO boundary bootstrap full inverse differs')
    result_tree=ast.parse(result);new_call=_source_call(result_tree,source)
    old_call.args[0].value=new_call.args[0].value=b'__E_SOLE_GO_LITERAL__'
    _need(ast.dump(previous_tree,include_attributes=False)==ast.dump(result_tree,include_attributes=False),'E sole-GO boundary non-source AST differs')
    return result,{'input':BOOT_BEFORE,'output':BOOT_AFTER,'owned_regions':1,'protected_gaps':2,'full_inverse':True,
                   'actual_dead_score_square_depth_order_keyword_cross_and_compiler_group_chain_consumed':True,
                   'source_AST_bytes_exact':True,'all_non_source_AST_and_bytes_equal':True,'external_reads':0}
