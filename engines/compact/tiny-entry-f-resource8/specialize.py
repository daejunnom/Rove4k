"""Fixed late-full-F workers8/TT18 v9 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector and all-eight job depth reset.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(7885, '47419319e3bfa0eb0e43a9ced1705c7f6283218af8a92157bda47c49ac2dd852')
OUTPUT=(7923, 'c3a389c3ef46ccf23a7e56f8e27c806f0f1f7545cd1e28f99ad6278acef4d057')
EDITS=((546, 546, b'X U[2]', b'X U[8]'), (5446, 5446, b'static S C=2,A', b'static S C=8,A'), (5772, 5772, b'X*w=U+(U[1].b>U->b);', b'X*w=U;for(S i=1;i<8;i++)if(U[i].b>w->b)w=U+i;'), (7048, 7073, b'pthread_mutex_lock(&J);C=2;U->b=U[1].b=-1;', b'pthread_mutex_lock(&J);C=8;for(S i=0;i<8;i++)U[i].b=-1;'), (7156, 7194, b'pthread_t a[2]', b'pthread_t a[8]'), (7256, 7294, b'for(;d<2;d++){U[d].a=d;', b'for(;d<8;d++){U[d].a=d;'))
GAPS=((0, 0, 546, '334a3e5737a7dea71d3225820efd3e88cf731ff83d48cdcf5fe0e2eb431f1f43'), (552, 552, 4894, '751471906d44686c025ae2959c6773706f5d3df9ee432096aba10d6c958e80ee'), (5460, 5460, 312, '904b82e48eed8bcdaa253d30893f4000bd6841bbb2a20d820bde154856761791'), (5792, 5817, 1256, '5f16777161e264c7a78849d7609a8c4b7e678a7ee49aa350b39c18d16a00c677'), (7090, 7128, 66, 'b89e7d17156013dc9588e1c486e16cd2d27388e89828684a65bd66bd20d6d6e4'), (7170, 7208, 86, '9ccb07c9704f7d0c8802ad6a55677aaf988fe759458c9ab0198fc6057d6e002c'), (7279, 7317, 606, 'a364249fc8966aa1327c2c2e593c5f8a4894faf909eff19037ee802f8c8121d2'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'job_pending_and_all_depth_reset_publication', 'thread_handle_array', 'create_success_count_limit')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F7885 fixed8/TT18 input admitted')
    result=source
    for old_at,new_at,old,new in reversed(EDITS):
        if source[old_at:old_at+len(old)]!=old:raise ValueError('fixed resource role differs')
        result=result[:old_at]+new+result[old_at+len(old):]
    inverse=result
    for old_at,new_at,old,new in reversed(EDITS):
        if result[new_at:new_at+len(new)]!=new:raise ValueError('fixed resource output role differs')
        inverse=inverse[:new_at]+old+inverse[new_at+len(new):]
    if _pin(result)!=OUTPUT or inverse!=source:raise ValueError('fixed resource output/full inverse differs')
    for old_at,new_at,length,digest in GAPS:
        a=source[old_at:old_at+length];b=result[new_at:new_at+length]
        if a!=b or hashlib.sha256(a).hexdigest()!=digest:raise ValueError('fixed resource protected gap differs')
    return result,{'input':INPUT,'output':OUTPUT,'workers':8,'TT_bits':18,'ply':128,
        'base_stage':'full-after-FROM-exact-inline','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':38,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
