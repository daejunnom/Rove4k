"""Fixed late-full-F workers8/TT18 v5 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(8153, '62784180e34291403f2ad32a314bd83fb9de9167d820960ffe0099402879a8dc')
OUTPUT=(8178, '070c54ea5e851fa37b7878e95d604a025b881c7901e491336ad260c4cf5613d2')
EDITS=((571, 571, b'zc qr[2]', b'zc qr[8]'), (5625, 5625, b'static S qk=2,qm', b'static S qk=8,qm'), (5995, 5995, b'zc*w=qr+(qr[1].b>qr->b);', b'zc*w=qr;for(S i=1;i<8;i++)if(qr[i].b>w->b)w=qr+i;'), (7312, 7337, b'pthread_mutex_lock(&qj);qk=2;qd++', b'pthread_mutex_lock(&qj);qk=8;qd++'), (7414, 7439, b'pthread_t a[2]', b'pthread_t a[8]'), (7518, 7543, b'for(;d<2;d++){qr[d].a=d;', b'for(;d<8;d++){qr[d].a=d;'))
GAPS=((0, 0, 571, 'c20b145195763543e352d98fa84c15f0629c44ff6409187c921749f1001fcfd1'), (579, 579, 5046, '49bf92470811a4a6c47f78038ab90a04e972a4fa241127bec4e0f1cbc50ed1b8'), (5641, 5641, 354, '48dc515cd27dc83fdb0d44382d2700692acc96132c1f8484f491d5b991a127fa'), (6019, 6044, 1293, '518fd34a43583fc0948442c8c1509f608385dcadb92f06b3f75a73afc73cf51c'), (7345, 7370, 69, '4a6d4ebf0a27763d491556e37cb764bc75846789d66e83e17edb842ed538f922'), (7428, 7453, 90, '7335a183c73a92909577ab1a75b79784a5c82d4e2ee3a188fabe920d309535a0'), (7542, 7567, 611, '25b0a1f566553cddf3ac30a58d49c46e44758f48adcea26696a10b5213d9dd8c'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'job_pending_publication', 'thread_handle_array', 'create_success_count_limit')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F8153 fixed8/TT18 input admitted')
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
        'base_stage':'full-after-four-locals','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':25,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
