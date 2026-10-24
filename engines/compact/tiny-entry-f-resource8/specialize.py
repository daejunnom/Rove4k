"""Fixed late-full-F workers8/TT18 v10 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector and all-eight job depth reset.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(7840, '67279ef99a5ade0b3b8c66564abc15e4ccd9bead3253ca18e4b88b6d87e14ca1')
OUTPUT=(7878, 'ce54ace72c9c903ea555347ffab4a0bc4635b0c48c70c6c5409ecaa66b657373')
EDITS=((544, 544, b'X U[2]', b'X U[8]'), (5424, 5424, b'static S C=2,A', b'static S C=8,A'), (5750, 5750, b'X*w=U+(U[1].b>U->b);', b'X*w=U;for(S i=1;i<8;i++)if(U[i].b>w->b)w=U+i;'), (6716, 6741, b'pthread_t a[2]', b'pthread_t a[8]'), (6816, 6841, b'for(;d<2;d++){U[d].a=d;', b'for(;d<8;d++){U[d].a=d;'), (7589, 7614, b'pthread_mutex_lock(&J);C=2;U->b=U[1].b=-1;', b'pthread_mutex_lock(&J);C=8;for(S i=0;i<8;i++)U[i].b=-1;'))
GAPS=((0, 0, 544, '559c9472bb4bd58358e8a15e8de2c49e8e7309755736a2f838e708142e48144e'), (550, 550, 4874, 'd1677a42233a3982bdf1a901cec3c50dd37013376e186a8b706d2a55704d14ac'), (5438, 5438, 312, '904b82e48eed8bcdaa253d30893f4000bd6841bbb2a20d820bde154856761791'), (5770, 5795, 946, '4b2508e8913b0ae953b7a45b8838f8b550515ce14cc84fc8ab65e475d5cf37b4'), (6730, 6755, 86, '9ccb07c9704f7d0c8802ad6a55677aaf988fe759458c9ab0198fc6057d6e002c'), (6839, 6864, 750, 'd4910fbbd2ccbd891f97aa875ae55c10320e224221149f83d17e2d3e0bc79f90'), (7631, 7669, 209, '7d7ec01ca8fd0759326d673ac4875ac59338e87a04400291301c3546a45142f7'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'thread_handle_array', 'create_success_count_limit', 'job_pending_and_all_depth_reset_publication')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F7840 fixed8/TT18 input admitted')
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
        'base_stage':'full-after-MTD-state-and-sole-GO','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':38,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
