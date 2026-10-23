"""Fixed late-full-F workers8/TT18 v4 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(8167, 'd9cb34ee6302822ab5a1b399039809d10be74cf69d50cc0ba3a14ecbdac6e86a')
OUTPUT=(8192, '100fcb8a115047554ccde6052caf7ee648e042668e650ca8fe2820d46d56619c')
EDITS=((571, 571, b'zc qr[2]', b'zc qr[8]'), (5637, 5637, b'static S qk=2,qm', b'static S qk=8,qm'), (6007, 6007, b'zc*w=qr+(qr[1].b>qr->b);', b'zc*w=qr;for(S i=1;i<8;i++)if(qr[i].b>w->b)w=qr+i;'), (7326, 7351, b'pthread_mutex_lock(&qj);qk=2;qd++', b'pthread_mutex_lock(&qj);qk=8;qd++'), (7428, 7453, b'pthread_t a[2]', b'pthread_t a[8]'), (7532, 7557, b'for(;d<2;d++){qr[d].a=d;', b'for(;d<8;d++){qr[d].a=d;'))
GAPS=((0, 0, 571, 'c20b145195763543e352d98fa84c15f0629c44ff6409187c921749f1001fcfd1'), (579, 579, 5058, 'c8560e49def64d0ff494ef600cbc49877ea892a4386d7f8b09ea29bec82bd341'), (5653, 5653, 354, '48dc515cd27dc83fdb0d44382d2700692acc96132c1f8484f491d5b991a127fa'), (6031, 6056, 1295, '602c69b74e1142310632e3b4d7ea357fa2a233b18ad8df999adb0b760a7fd107'), (7359, 7384, 69, '4a6d4ebf0a27763d491556e37cb764bc75846789d66e83e17edb842ed538f922'), (7442, 7467, 90, '7335a183c73a92909577ab1a75b79784a5c82d4e2ee3a188fabe920d309535a0'), (7556, 7581, 611, '25b0a1f566553cddf3ac30a58d49c46e44758f48adcea26696a10b5213d9dd8c'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'job_pending_publication', 'thread_handle_array', 'create_success_count_limit')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F8167 fixed8/TT18 input admitted')
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
        'base_stage':'full-after-return-token','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':25,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
