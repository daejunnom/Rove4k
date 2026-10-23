"""Fixed late-full-F workers8/TT18 v6 specialization; no IO in API.
Declared resource-profile specialization, not fixed2 behavior identity.
Six fixed roles: arrays/startup/GO/create count and strict depth8 selector and all-eight job depth reset.
All one-condition startup/completion broadcasts and predicates stay intact.
No compiler/codec/runtime evidence is supplied by this source transform.
"""
import hashlib
INPUT=(8094, '543b6469c4f5ec616cde0e5113fa15c1419651a414717b9e25c498044369a79e')
OUTPUT=(8131, '7245231f4de125a0daeff3bdde0501c698d6094c9461e7d3b8c8a139247de333')
EDITS=((571, 571, b'zc qr[2]', b'zc qr[8]'), (5563, 5563, b'static S qk=2,qm', b'static S qk=8,qm'), (5933, 5933, b'zc*w=qr+(qr[1].b>qr->b);', b'zc*w=qr;for(S i=1;i<8;i++)if(qr[i].b>w->b)w=qr+i;'), (7241, 7266, b'pthread_mutex_lock(&qj);qk=2;qr->b=qr[1].b=-1;', b'pthread_mutex_lock(&qj);qk=8;for(S i=0;i<8;i++)qr[i].b=-1;'), (7355, 7392, b'pthread_t a[2]', b'pthread_t a[8]'), (7459, 7496, b'for(;d<2;d++){qr[d].a=d;', b'for(;d<8;d++){qr[d].a=d;'))
GAPS=((0, 0, 571, 'c20b145195763543e352d98fa84c15f0629c44ff6409187c921749f1001fcfd1'), (579, 579, 4984, 'a46600ab37f624f7b4425c819e456e7c3001fdf6b9728842508174429189c166'), (5579, 5579, 354, '48dc515cd27dc83fdb0d44382d2700692acc96132c1f8484f491d5b991a127fa'), (5957, 5982, 1284, 'abefe67cc52ed97fd19759cc528af9e5621429b27c403b3714870b8af1a567c1'), (7287, 7324, 68, '58f058ebdc54c28fcb66b02a02b5fb518f38da75a02113215bf19f076450d864'), (7369, 7406, 90, '7335a183c73a92909577ab1a75b79784a5c82d4e2ee3a188fabe920d309535a0'), (7483, 7520, 611, '25b0a1f566553cddf3ac30a58d49c46e44758f48adcea26696a10b5213d9dd8c'))
ROLES=('worker_state_array', 'startup_ready_pending', 'completed_result_depth_scan', 'job_pending_and_all_depth_reset_publication', 'thread_handle_array', 'create_success_count_limit')

def _pin(raw):return len(raw),hashlib.sha256(raw).hexdigest()
def transform_source(source,workers=8,tt_bits=18,family='F'):
    if (family,workers,tt_bits)!=('F',8,18) or type(source)is not bytes or _pin(source)!=INPUT:
        raise ValueError('only pinned late full-F8094 fixed8/TT18 input admitted')
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
        'base_stage':'full-after-tt-pool','roles':ROLES,
        'spans':6,'protected_gaps':7,'gaps':GAPS,'raw_delta':37,'full_inverse':True,'all_gaps_equal':True,
        'edits':[{'role':role,'old_start':a,'new_start':b,'old':old.decode(),'new':new.decode()}
                 for role,(a,b,old,new)in zip(ROLES,EDITS)],
        'main_threads':1,'native_TIDs_if_all_creates_succeed':9,
        'same_condition_predicates_broadcast4_signal0_wait2':True,
        'shutdown_joins_actual_created_count':True,'native_whole_runtime_claimed':False,
        'external_reads':0,'compiler_codec_PP_engine_runtime_calls':0}
