"""Fixed late-full-F workers8/TT18 v3 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(8360, 'b4e8f79615eb08c4d5dcb8db9e1cac76cecbef172f2096c64cafcebbc54cabf8')
OUTPUT=(8385, 'a9237511e92c83ee8a2d07b555cfca886733282b77eca2f0e74d74890d9df2e0')
EDITS=((554, 554, b'zc qr[2]', b'zc qr[8]'), (5770, 5770, b'static S qk=2,qm', b'static S qk=8,qm'), (6155, 6155, b'zc*w=qr+(qr[1].b>qr->b);', b'zc*w=qr;for(S i=1;i<8;i++)if(qr[i].b>w->b)w=qr+i;'), (7509, 7534, b'pthread_mutex_lock(&qj);qk=2;qd++', b'pthread_mutex_lock(&qj);qk=8;qd++'), (7611, 7636, b'pthread_t a[2]', b'pthread_t a[8]'), (7720, 7745, b'for(;d<2;d++){qr[d].a=d;', b'for(;d<8;d++){qr[d].a=d;'))
GAPS=((0, 0, 554, 'f05382084fac6a4de957bcbb7c7646eedf2818a4405297c4de003c4344d7c03f'), (562, 562, 5208, '02f369d5feeb2f43993279d2622b1a8653a14c3e12be64c11bf6ed5c8e862c3d'), (5786, 5786, 369, '4b614a16657a22e31ffecdeb1b497cb8961130d01b73301826ed9149456241a4'), (6179, 6204, 1330, '7edfee920aeb837e98f7bb1c49ec475340e83599141bb8e815c92b5e6f999035'), (7542, 7567, 69, '4a6d4ebf0a27763d491556e37cb764bc75846789d66e83e17edb842ed538f922'), (7625, 7650, 95, 'd0dec792d9337198c9389f544caf67e608284bbc19c4b88c3f5345ff95de6c9c'), (7744, 7769, 616, '8d5022ebb8fcc08279b2d6f735e0b1f2187e361672d9b73961da5bb5a59f5d31'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'job_pending_publication', 'thread_handle_array', 'create_success_count_limit')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F8360 fixed8/TT18 input admitted')
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
        'base_stage':'full-after-valid-square-successor','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':25,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
